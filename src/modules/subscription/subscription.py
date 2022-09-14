# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
import json
import logging
import typing as t

from flask import g

from src.modules.auth.auth import Auth
from src.modules.auth.user import UserManager
from src.modules.database.mongodb_client import MongodbClient
from src.modules.payment.order import OrderManager
from src.modules.subscription.vault import VaultManager
from src.utils.consts import VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_MODIFY_TIME, VAULT_SERVICE_PRICING_USING
from src.utils.did.did_wrapper import DID, DIDDocument
from src.utils.payment_config import PaymentConfig
from src.utils.http_exception import BadRequestException, ApplicationNotFoundException
from src.utils.singleton import Singleton


class VaultSubscription(metaclass=Singleton):
    """ The vault is keeping the user's data and files.

    One user can only have one vault on one node.
    """

    def __init__(self):
        self.auth = Auth()
        self.mcli = MongodbClient()
        self.user_manager = UserManager()
        self.order_manager = OrderManager()
        self.vault_manager = VaultManager()

    def subscribe(self):
        """ :v2 API: """

        plan = PaymentConfig.get_vault_plan('Free')
        return self.__get_vault_info(self.vault_manager.create_vault(g.usr_did, plan))

    def __get_vault_info(self, vault, files_used=False):
        info = {
            'service_did': self.auth.get_did_string(),
            'pricing_plan': vault[VAULT_SERVICE_PRICING_USING],
            'storage_quota': vault.get_storage_quota(),
            'storage_used': vault.get_storage_usage(),
            'start_time': int(vault[VAULT_SERVICE_START_TIME]),
            'end_time': int(vault[VAULT_SERVICE_END_TIME]),
            'created': int(vault[VAULT_SERVICE_START_TIME]),
            'updated': int(vault[VAULT_SERVICE_MODIFY_TIME]),
        }

        if files_used:
            info['files_used'] = vault.get_files_usage()

        return info

    def unsubscribe(self):
        """ :v2 API: """
        vault = self.vault_manager.get_vault(g.usr_did)

        logging.debug(f'start remove the vault of the user {g.usr_did}, _id, {str(vault["_id"])}')

        # archive orders as orders are important information.
        self.order_manager.archive_orders_receipts(g.usr_did)

        # remove the data and info. of the vault.
        self.vault_manager.remove_vault(g.usr_did)

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
        """ List the applications belongs to this vault.

        :v2 API: """

        app_dids = self.user_manager.get_apps(g.usr_did)

        def get_app_detail(user_did, app_did):
            info = {}
            try:
                info = VaultSubscription.__get_appdid_info_by_did(app_did)
            except Exception as e:
                logging.error(f'get the info of the app did {app_did} failed: {str(e)}')

            return {
                "name": info.get('name', ''),
                "developer_did": info.get('developer', ''),
                "icon_url": info.get('icon_url', ''),
                "redirect_url": info.get('redirect_url', ''),
                "user_did": user_did,
                "app_did": app_did,
                "used_storage_size": int(self.vault_manager.count_app_files_total_size(user_did, app_did)
                                         + self.vault_manager.get_user_database_size(user_did, app_did))
            }

        results = list(filter(lambda b: b is not None, map(lambda app_did: get_app_detail(g.usr_did, app_did), app_dids)))
        if not results:
            raise ApplicationNotFoundException()

        return {"apps": results}

    @staticmethod
    def __get_appdid_info_by_did(did_str: str):
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

        def get_info_from_credential(fragment: str, props_callback: t.Callable[[dict], dict]) -> dict:
            """ Get the information from the credential. """
            vc = doc.get_credential(did, fragment)
            if not vc.is_valid():
                logging.error('The credential is not valid.')
                return {}
            return props_callback(json.loads(vc.to_json()))

        info = get_info_from_credential('appinfo', get_appinfo_props)
        info.update(get_info_from_credential('developer', get_developer_props))
        return info
