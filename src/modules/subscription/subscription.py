# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
import json
import logging
from datetime import datetime
import typing as t

from flask import g

from src import hive_setting
from src.modules.auth.auth import Auth
from src.modules.auth.user import UserManager
from src.modules.payment.order import OrderManager
from src.modules.subscription.vault import VaultManager, Vault
from src.utils.consts import IS_UPGRADED
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_MAX_STORAGE, \
    VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, \
    VAULT_SERVICE_MODIFY_TIME, VAULT_SERVICE_STATE, VAULT_SERVICE_PRICING_USING, VAULT_SERVICE_STATE_RUNNING
from src.utils.did.did_wrapper import DID, DIDDocument
from src.utils_v1.payment.payment_config import PaymentConfig
from src.utils.db_client import cli
from src.utils.file_manager import fm
from src.utils.http_exception import AlreadyExistsException, NotImplementedException, VaultNotFoundException, \
    PricePlanNotFoundException, BadRequestException, ApplicationNotFoundException
from src.utils.singleton import Singleton


class VaultSubscription(metaclass=Singleton):
    def __init__(self):
        self.auth = Auth()
        self.user_manager = UserManager()
        self.order_manager = OrderManager()
        self.vault_manager = VaultManager()

    def subscribe(self):
        """ :v2 API: """
        self.get_checked_vault(g.usr_did, is_not_exist_raise=False)
        return self.__get_vault_info(self.create_vault(g.usr_did, self.get_price_plan('vault', 'Free')))

    def create_vault(self, user_did, price_plan, is_upgraded=False):
        now = datetime.now().timestamp()  # seconds in UTC
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {VAULT_SERVICE_DID: user_did,
               VAULT_SERVICE_MAX_STORAGE: int(price_plan["maxStorage"]) * 1024 * 1024,  # unit: byte (MB on v1, checked by 1024 * 1024)
               VAULT_SERVICE_FILE_USE_STORAGE: 0,  # unit: byte
               VAULT_SERVICE_DB_USE_STORAGE: 0,  # unit: byte
               IS_UPGRADED: is_upgraded,  # True, the vault is from the promotion.
               VAULT_SERVICE_START_TIME: now,
               VAULT_SERVICE_END_TIME: end_time,
               VAULT_SERVICE_MODIFY_TIME: now,
               VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING,
               VAULT_SERVICE_PRICING_USING: price_plan['name']}
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, doc, create_on_absence=True, is_extra=False)
        # INFO: user database will create with first collection creation.
        if not fm.create_dir(hive_setting.get_user_vault_path(user_did)):
            raise BadRequestException('Failed to create folder for the user.')
        return doc

    def __get_vault_info(self, doc, files_used=False):
        vault = Vault(**doc)
        info = {
            'service_did': self.auth.get_did_string(),
            'pricing_plan': doc[VAULT_SERVICE_PRICING_USING],
            'storage_quota': vault.get_storage_quota(),
            'storage_used': vault.get_storage_usage(),
            'start_time': int(doc[VAULT_SERVICE_START_TIME]),
            'end_time': int(doc[VAULT_SERVICE_END_TIME]),
            'created': cli.timestamp_to_epoch(doc[VAULT_SERVICE_START_TIME]),
            'updated': cli.timestamp_to_epoch(doc[VAULT_SERVICE_MODIFY_TIME]),
        }

        if files_used:
            info['files_used'] = vault.get_files_usage()

        return info

    def unsubscribe(self):
        """ :v2 API: """
        doc = self.get_checked_vault(g.usr_did)

        logging.debug(f'start remove the vault of the user {g.usr_did}, _id, {str(doc["_id"])}')

        self.vault_manager.drop_vault_data(g.usr_did)
        self.order_manager.archive_orders_receipts(g.usr_did)
        # INFO: maybe user has a backup service
        # self.user_manager.remove_user(g.usr_did)

        cli.delete_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: g.usr_did}, is_check_exist=False)

    def activate(self):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)
        self.vault_manager.activate_vault(g.usr_did, is_activate=True)

    def deactivate(self):
        """ :v2 API: """
        self.vault_manager.get_vault(g.usr_did)
        self.vault_manager.activate_vault(g.usr_did, is_activate=False)

    def get_info(self, files_used: bool):
        """ :v2 API:

        :param files_used for files usage testing
        """
        vault = self.vault_manager.get_vault(g.usr_did)
        return self.__get_vault_info(vault, files_used)

    def get_app_stats(self):
        """ :v2 API: """
        app_dids = self.user_manager.get_apps(g.usr_did)
        results = list(filter(lambda b: b is not None, map(lambda app_did: self.get_app_detail(g.usr_did, app_did), app_dids)))
        if not results:
            raise ApplicationNotFoundException()
        return {"apps": results}

    def get_app_detail(self, user_did, app_did):
        info = {}
        try:
            info = self._get_appdid_info_by_did(app_did)
        except Exception as e:
            logging.error(f'get the info of the app did {app_did} failed: {str(e)}')
        name = cli.get_user_database_name(user_did, app_did)
        return {
            "name": info.get('name', ''),
            "developer_did": info.get('developer', ''),
            "icon_url": info.get('icon_url', ''),
            "redirect_url": info.get('redirect_url', ''),
            "user_did": user_did,
            "app_did": app_did,
            "used_storage_size": int(fm.ipfs_get_app_file_usage(name) + cli.get_database_size(name))
        }

    def get_price_plans(self, subscription, name):
        all_plans = PaymentConfig.get_all_package_info()
        result = {'version': all_plans.get('version', '1.0')}
        if subscription == 'all':
            result['backupPlans'] = self.__filter_plans_by_name(all_plans.get('backupPlans', []), name)
            result['pricingPlans'] = self.__filter_plans_by_name(all_plans.get('pricingPlans', []), name)
            if not result['backupPlans'] and not result['pricingPlans']:
                raise PricePlanNotFoundException()
        elif subscription == 'vault':
            result['pricingPlans'] = self.__filter_plans_by_name(all_plans.get('pricingPlans', []), name)
            if not result['pricingPlans']:
                raise PricePlanNotFoundException()
        elif subscription == 'backup':
            result['backupPlans'] = self.__filter_plans_by_name(all_plans.get('backupPlans', []), name)
            if not result['backupPlans']:
                raise PricePlanNotFoundException()
        return result

    def get_price_plan(self, subscription, name):
        all_plans = PaymentConfig.get_all_package_info()
        plans = []
        if subscription == 'vault':
            plans = self.__filter_plans_by_name(all_plans.get('pricingPlans', []), name)
        elif subscription == 'backup':
            plans = self.__filter_plans_by_name(all_plans.get('backupPlans', []), name)
        return plans[0] if plans else None

    def __filter_plans_by_name(self, plans, name):
        if not name:
            return plans
        return list(filter(lambda p: p.get('name') == name, plans))

    def get_price_plans_version(self):
        return PaymentConfig.get_all_package_info().get('version', '1.0')

    def get_checked_vault(self, user_did, throw_exception=True, is_not_exist_raise=True):
        """ get the information of the vault which need check first.
        :param user_did: user DID
        :param throw_exception: throw VaultNotFoundException if is_not_exist_raise is True else throw AlreadyExistsException
        :return: the information of the vault.
        """
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: user_did},
                                  create_on_absence=True, throw_exception=False)
        if throw_exception and is_not_exist_raise and not doc:
            raise VaultNotFoundException()
        if throw_exception and not is_not_exist_raise and doc:
            raise AlreadyExistsException('The vault already exists.')
        return doc

    def _get_remain_days(self, cur_plan, cur_end_timestamp, now_timestamp, plan):
        if cur_plan['amount'] < 0.01 or cur_plan['serviceDays'] == -1 or cur_end_timestamp == -1:
            return 0
        if plan['amount'] < 0.01 or plan['serviceDays'] == -1:
            return 0
        if cur_end_timestamp <= now_timestamp:
            return 0
        days = (cur_end_timestamp - now_timestamp) / (24 * 60 * 60)
        return days * cur_plan['amount'] / plan['amount']

    def get_vault_max_size(self, user_did):
        doc = self.get_checked_vault(user_did, throw_exception=True)
        return doc[VAULT_SERVICE_MAX_STORAGE]

    def _get_info_from_credential(self, did: DID, doc: DIDDocument, fragment: str, props_callback: t.Callable[[dict], dict]) -> dict:
        """ Get the information from the credential. """
        vc = doc.get_credential(did, fragment)
        if not vc.is_valid():
            logging.error('The credential is not valid.')
            return {}
        return props_callback(json.loads(vc.to_json()))

    def _get_appdid_info_by_did(self, did_str: str):
        """ Get the information from the service did. """
        logging.info(f'get_appdid_info: did, {did_str}')
        if not did_str:
            raise BadRequestException('get_appdid_info: did must provide.')

        did: DID = DID.from_string(did_str)
        doc: DIDDocument = did.resolve()

        def get_appinfo_props(vc_json: dict) -> dict:
            props = {'name': '', 'icon_url': '', 'redirect_url': ''}
            if 'credentialSubject' in vc_json:
                cs = vc_json['credentialSubject']
                props['name'] = cs.get('name', '')
                props['icon_url'] = cs.get('iconUrl', '')
                if 'endpoints' in vc_json:
                    props['icon_url'] = cs['endpoints'].get('redirectUrl', '')
            return props

        def get_developer_props(vc_json: dict):
            return {'developer_did': vc_json.get('issuer', '')}

        info = self._get_info_from_credential(did, doc, 'appinfo', get_appinfo_props)
        info.update(self._get_info_from_credential(did, doc, 'developer', get_developer_props))
        return info
