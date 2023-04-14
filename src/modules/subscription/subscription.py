# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
import json
import logging
import typing as t

from flask import g

from src.modules.auth.auth import Auth
from src.modules.subscription.vault import Vault
from src.modules.database.mongodb_client import MongodbClient, mcli
from src.modules.payment.order import OrderManager
from src.utils.did.eladid_wrapper import DID, DIDDocument, DIDURL
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
        self.order_manager = OrderManager()

    def subscribe(self):
        """ :v2 API: """

        plan = PaymentConfig.get_free_vault_plan()
        return self.__get_vault_info(mcli.get_col_vault().create_vault(g.usr_did, plan))

    def __get_vault_info(self, vault: Vault, files_used=False):
        info = {
            'service_did': self.auth.get_did_string(),
            'pricing_plan': vault.get_plan_name(),
            'storage_quota': vault.get_storage_quota(),
            'storage_used': vault.get_storage_usage(),
            'start_time': int(vault.get_started_time()),
            'end_time': int(vault.get_end_time()),
            'created': int(vault.get_started_time()),
            'updated': int(vault.get_modified_time()),
            'app_count': len(mcli.get_col_application().get_apps(g.usr_did))
        }

        if files_used:
            info['files_used'] = vault.get_files_usage()

        info.update(mcli.get_col_vault().get_vault_access_statistics(g.usr_did))
        return info

    def unsubscribe(self, force):
        """ :v2 API: """
        vault = mcli.get_col_vault().get_vault(g.usr_did)

        logging.debug(f'start remove the vault of the user={g.usr_did}, _id={str(vault["_id"])}, force={force}')

        if force:
            # archive orders as orders are important information.
            self.order_manager.archive_orders_receipts(g.usr_did)

        # remove the data and info. of the vault.
        mcli.get_col_vault().remove_vault(g.usr_did, force)

    def activate(self):
        """ :v2 API: """
        mcli.get_col_vault().get_vault(g.usr_did)
        mcli.get_col_vault().activate_vault(g.usr_did, is_activate=True)

    def deactivate(self):
        """ :v2 API: """
        mcli.get_col_vault().get_vault(g.usr_did)
        mcli.get_col_vault().activate_vault(g.usr_did, is_activate=False)

    def get_info(self, files_used: bool):
        """ :v2 API:

        :param files_used for files usage testing
        """
        vault = mcli.get_col_vault().get_vault(g.usr_did)
        return self.__get_vault_info(vault, files_used)

    def get_app_stats(self):
        """ List the applications belongs to this vault.

        :v2 API: """

        apps = mcli.get_col_application().get_apps(g.usr_did)

        def get_app_detail(user_did, app):
            app_did, info = app[mcli.get_col_application().APP_DID], {}
            try:
                info = VaultSubscription.__get_appdid_info_by_did(app_did)
            except Exception as e:
                logging.error(f'get the info of the app did {app_did} failed: {str(e)}')

            col_application = mcli.get_col_application()
            return {
                "name": info.get('name', ''),
                "developer_did": info.get('developer', ''),
                "icon_url": info.get('icon_url', ''),
                "redirect_url": info.get('redirect_url', ''),
                "user_did": user_did,
                "app_did": app_did,
                "used_storage_size": col_application.get_app_storage_used_size(user_did, app_did),
                "access_count": app.get(col_application.ACCESS_COUNT, 0),
                "access_amount": app.get(col_application.ACCESS_AMOUNT, 0),
                "access_last_time": app.get(col_application.ACCESS_LAST_TIME, -1),
            }

        results = list(filter(lambda b: b is not None, map(lambda app: get_app_detail(g.usr_did, app), apps)))
        if not results:
            raise ApplicationNotFoundException()

        return {"apps": results}

    def delete_app(self):
        mcli.get_col_vault().remove_vault_app(g.usr_did, g.app_did)

    @staticmethod
    def __get_appdid_info_by_did(did_str: str):
        """ Get the information from the service did. """
        logging.info(f'get_appdid_info: did, {did_str}')
        if not did_str:
            raise BadRequestException('get_appdid_info: did must provide.')

        did: DID = DID.create_from_str(did_str)
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
            vc = doc.get_credential(DIDURL.create_from_did(did, fragment))
            if not vc.is_valid():
                logging.error('The credential is not valid.')
                return {}
            return props_callback(json.loads(vc.to_json()))

        info = {}
        try:
            info.update(get_info_from_credential('appinfo', get_appinfo_props))
        except Exception as e:
            logging.error(f'Failed to get "appinfo" of the app did: {e}')
        try:
            info.update(get_info_from_credential('developer', get_developer_props))
        except Exception as e:
            logging.error(f'Failed to get "developer" of the app did: {e}')
        return info
