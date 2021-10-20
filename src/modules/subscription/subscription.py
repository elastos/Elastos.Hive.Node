# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
from datetime import datetime

from src.utils.consts import IS_UPGRADED
from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_MAX_STORAGE, \
    VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, \
    VAULT_SERVICE_MODIFY_TIME, VAULT_SERVICE_STATE, VAULT_SERVICE_PRICING_USING
from src.utils_v1.did_file_info import get_vault_path
from src.utils_v1.payment.payment_config import PaymentConfig
from src.utils_v1.payment.vault_service_manage import delete_user_vault_data
from src.modules.payment.payment import Payment
from src.utils.db_client import cli, VAULT_SERVICE_STATE_RUNNING
from src.utils.did_auth import check_auth
from src.utils.file_manager import fm
from src.utils.http_exception import AlreadyExistsException, NotImplementedException, VaultNotFoundException, \
    PricePlanNotFoundException, BadRequestException
from src.utils.http_response import hive_restful_response
from src.utils.singleton import Singleton
from src.utils_v1.auth import get_current_node_did_string


class VaultSubscription(metaclass=Singleton):
    def __init__(self):
        self.payment = Payment()

    @hive_restful_response
    def subscribe(self):
        user_did, app_did = check_auth()
        self.get_checked_vault(user_did, is_not_exist_raise=False)
        return self.__get_vault_info(self.create_vault(user_did, self.get_price_plan('vault', 'Free')))

    def create_vault(self, user_did, price_plan, is_upgraded=False):
        now = datetime.utcnow().timestamp()  # seconds in UTC
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {VAULT_SERVICE_DID: user_did,
               VAULT_SERVICE_MAX_STORAGE: int(price_plan["maxStorage"]) * 1024 * 1024,
               VAULT_SERVICE_FILE_USE_STORAGE: 0,
               VAULT_SERVICE_DB_USE_STORAGE: 0,
               IS_UPGRADED: is_upgraded,
               VAULT_SERVICE_START_TIME: now,
               VAULT_SERVICE_END_TIME: end_time,
               VAULT_SERVICE_MODIFY_TIME: now,
               VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING,
               VAULT_SERVICE_PRICING_USING: price_plan['name']}
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, doc, create_on_absence=True, is_extra=False)
        # INFO: user database will create with first collection creation.
        if not fm.create_dir(get_vault_path(user_did)):
            raise BadRequestException('Failed to create folder for the user.')
        return doc

    def __get_vault_info(self, doc):
        storage_quota = int(doc[VAULT_SERVICE_MAX_STORAGE] * 1024 * 1024) \
                        if int(doc[VAULT_SERVICE_MAX_STORAGE]) < 1024 * 1024 \
                        else int(doc[VAULT_SERVICE_MAX_STORAGE])
        storage_used = int(doc[VAULT_SERVICE_FILE_USE_STORAGE] + doc[VAULT_SERVICE_DB_USE_STORAGE])
        return {
            'pricing_plan': doc[VAULT_SERVICE_PRICING_USING],
            'service_did': get_current_node_did_string(),
            'storage_quota': storage_quota,
            'storage_used': storage_used,
            'created': cli.timestamp_to_epoch(doc[VAULT_SERVICE_START_TIME]),
            'updated': cli.timestamp_to_epoch(doc[VAULT_SERVICE_MODIFY_TIME]),
        }

    @hive_restful_response
    def unsubscribe(self):
        user_did, app_did = check_auth()
        document = self.get_checked_vault(user_did, throw_exception=False)
        if not document:
            # INFO: do not raise here.
            return
        delete_user_vault_data(user_did)
        cli.remove_database(user_did, app_did)
        self.payment.archive_orders(user_did)
        cli.delete_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: user_did}, is_check_exist=False)

    @hive_restful_response
    def activate(self):
        raise NotImplementedException()

    @hive_restful_response
    def deactivate(self):
        raise NotImplementedException()

    def __update_vault_state(self, status):
        user_did, app_did = check_auth()
        self.get_checked_vault(user_did)
        col_filter = {VAULT_SERVICE_DID: user_did}
        doc = {VAULT_SERVICE_DID: user_did,
               VAULT_SERVICE_MODIFY_TIME: datetime.utcnow().timestamp(),
               VAULT_SERVICE_STATE: status}
        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, col_filter, {"$set": doc})

    @hive_restful_response
    def get_info(self):
        user_did, app_did = check_auth()
        doc = self.get_checked_vault(user_did)
        return self.__get_vault_info(doc)

    @hive_restful_response
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
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: user_did},
                                  create_on_absence=True, throw_exception=False)
        if throw_exception and is_not_exist_raise and not doc:
            raise VaultNotFoundException()
        if throw_exception and not is_not_exist_raise and doc:
            raise AlreadyExistsException(msg='The vault already exists.')
        return doc

    def upgrade_vault_plan(self, user_did, vault, pricing_name):
        remain_days = 0
        now = datetime.utcnow().timestamp()  # seconds in UTC
        plan = self.get_price_plan('vault', pricing_name)
        if vault[VAULT_SERVICE_END_TIME] != -1:
            cur_plan = self.get_price_plan('vault', vault[VAULT_SERVICE_PRICING_USING])
            remain_days = self._get_remain_days(cur_plan, vault[VAULT_SERVICE_END_TIME], now, plan)

        end_time = -1 if plan['serviceDays'] == -1 else now + (plan['serviceDays'] + remain_days) * 24 * 60 * 60
        col_filter = {VAULT_SERVICE_DID: user_did}
        update = {VAULT_SERVICE_PRICING_USING: pricing_name,
                  VAULT_SERVICE_MAX_STORAGE: int(plan["maxStorage"]) * 1024 * 1024,
                  VAULT_SERVICE_START_TIME: now,
                  VAULT_SERVICE_END_TIME: end_time,
                  VAULT_SERVICE_MODIFY_TIME: now,
                  VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING}

        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, col_filter, {"$set": update})

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
