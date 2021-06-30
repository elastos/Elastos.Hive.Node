# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
from datetime import datetime

from hive.main.view import h_auth
from hive.util.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_MAX_STORAGE, \
    VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, \
    VAULT_SERVICE_MODIFY_TIME, VAULT_SERVICE_STATE, VAULT_SERVICE_PRICING_USING
from hive.util.did_file_info import get_vault_path
from hive.util.payment.payment_config import PaymentConfig
from hive.util.payment.vault_service_manage import delete_user_vault_data
from src.modules.backup.backup_server import BackupServer
from src.modules.scripting.scripting import check_auth
from src.utils.db_client import cli, VAULT_SERVICE_STATE_RUNNING
from src.utils.file_manager import fm
from src.utils.http_exception import AlreadyExistsException, NotImplementedException, VaultNotFoundException, \
    PricePlanNotFoundException, BadRequestException
from src.utils.http_response import hive_restful_response


class VaultSubscription:
    def __init__(self):
        pass

    @hive_restful_response
    def subscribe(self, credential):
        if credential:
            # TODO: Need support this with payment.
            raise NotImplementedException(msg='Not support with credential.')
        return self.__subscribe_free()

    def __subscribe_free(self):
        did, app_id = check_auth()
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did}, is_create=True)
        if doc:
            raise AlreadyExistsException(msg='The vault is already subscribed.')
        return self.__get_vault_info(self.__create_vault(did, PaymentConfig.get_free_vault_info()))

    def __create_vault(self, did, price_plan):
        now = datetime.utcnow().timestamp()  # seconds in UTC
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60
        doc = {VAULT_SERVICE_DID: did,
               VAULT_SERVICE_MAX_STORAGE: int(price_plan["maxStorage"]) * 1000 * 1000,
               VAULT_SERVICE_FILE_USE_STORAGE: 0,
               VAULT_SERVICE_DB_USE_STORAGE: 0,
               VAULT_SERVICE_START_TIME: now,
               VAULT_SERVICE_END_TIME: end_time,
               VAULT_SERVICE_MODIFY_TIME: now,
               VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING,
               VAULT_SERVICE_PRICING_USING: price_plan['name']}
        cli.insert_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, doc, is_create=True)
        # INFO: user database will create with first collection creation.
        if not fm.create_dir(get_vault_path(did)):
            raise BadRequestException('Failed to create folder for the user.')
        return doc

    def __get_vault_info(self, doc):
        return {
            'pricing_plan': doc[VAULT_SERVICE_PRICING_USING],
            'service_did': h_auth.get_did_string(),
            'storage_quota': int(doc[VAULT_SERVICE_MAX_STORAGE]),
            'storage_used': int(doc[VAULT_SERVICE_FILE_USE_STORAGE]),
            'created': cli.timestamp_to_epoch(doc[VAULT_SERVICE_START_TIME]),
            'updated': cli.timestamp_to_epoch(doc[VAULT_SERVICE_MODIFY_TIME]),
        }

    @hive_restful_response
    def unsubscribe(self):
        did, app_id = check_auth()
        document = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did}, is_raise=False)
        if not document:
            return
        delete_user_vault_data(did)
        cli.remove_database(did, app_id)
        cli.delete_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did}, is_check_exist=False)

    @hive_restful_response
    def activate(self):
        raise NotImplementedException()

    @hive_restful_response
    def deactivate(self):
        raise NotImplementedException()

    def __update_vault_state(self, status):
        did, app_id = check_auth()

        col_filter = {VAULT_SERVICE_DID: did}
        document = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, col_filter)
        if not document:
            raise VaultNotFoundException()

        doc = {VAULT_SERVICE_DID: did,
               VAULT_SERVICE_MODIFY_TIME: datetime.utcnow().timestamp(),
               VAULT_SERVICE_STATE: status}
        cli.update_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, col_filter, {"$set": doc})

    @hive_restful_response
    def get_info(self):
        did, app_id = check_auth()
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {VAULT_SERVICE_DID: did}, is_raise=False)
        if not doc:
            raise VaultNotFoundException()
        return self.__get_vault_info(doc)

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

    def __filter_plans_by_name(self, plans, name):
        if not name:
            return plans
        return list(filter(lambda p: p.get('name') == name, plans))


class BackupSubscription:
    def __init__(self):
        self.server = BackupServer()

    @hive_restful_response
    def subscribe(self, credential):
        if credential:
            # TODO: Need support this with payment.
            raise NotImplementedException(msg='Not support with credential.')
        return self.server.subscribe_free()

    @hive_restful_response
    def unsubscribe(self):
        self.server.unsubscribe()

    @hive_restful_response
    def activate(self):
        raise NotImplementedException()

    @hive_restful_response
    def deactivate(self):
        raise NotImplementedException()

    @hive_restful_response
    def get_info(self):
        return self.server.get_info()
