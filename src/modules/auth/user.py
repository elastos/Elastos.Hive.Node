import logging

from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import COL_APPLICATION_USR_DID, COL_APPLICATION_APP_DID, COL_APPLICATION_STATE, COL_APPLICATION_STATE_NORMAL, COL_APPLICATION, \
    COL_APPLICATION_DATABASE_NAME, APP_ID, USER_DID, DID_INFO_REGISTER_COL


class UserManager:
    def __init__(self):
        self.mcli = MongodbClient()

    def get_temp_app_dids(self, user_did):
        """ Get all applications DIDs belonged to user DID in the 'auth_register' collection

        @deprecated Only for syncing app_dids from DID_INFO_REGISTER_COL to COL_APPLICATION
        """
        col = self.mcli.get_management_collection(DID_INFO_REGISTER_COL)
        # INFO: Must check the existence of some fields
        filter_ = {
            APP_ID: {'$exists': True},
            '$and': [{USER_DID: {'$exists': True}}, {USER_DID: user_did}]
        }
        docs = col.find_many(filter_)
        return list(set(map(lambda d: d[APP_ID], docs)))

    def get_user_count(self):
        col = self.mcli.get_management_collection(COL_APPLICATION)
        return len(col.distinct(USER_DID))

    def get_app_docs(self, user_did) -> list:
        """ get all application information by user did"""

        if not user_did:
            return []

        filter_ = {
            COL_APPLICATION_USR_DID: user_did,
        }

        col = self.mcli.get_management_collection(COL_APPLICATION)
        return col.find_many(filter_)

    def get_apps(self, user_did) -> list:
        """ get all application DIDs of the user did """
        return list(map(lambda d: d[COL_APPLICATION_APP_DID], self.get_app_docs(user_did)))

    def get_database_names(self, user_did) -> list:
        """ get all database names of the user did """
        return list(map(lambda d: d[COL_APPLICATION_DATABASE_NAME], self.get_app_docs(user_did)))

    def add_app_if_not_exists(self, user_did, app_did):
        """ add the relation of user did and app did to collection

        :param user_did can not be None
        :param app_did application did
        """

        if not user_did or not app_did:
            logging.getLogger('UserManager').error(f'Skip adding invalid user_did({user_did}) or app_did({app_did})')
            return

        filter_ = {
            COL_APPLICATION_USR_DID: user_did,
            COL_APPLICATION_APP_DID: app_did,
        }

        update = {'$set': {
            COL_APPLICATION_DATABASE_NAME: self.mcli.get_user_database_name(user_did, app_did),
            COL_APPLICATION_STATE: COL_APPLICATION_STATE_NORMAL}}

        col = self.mcli.get_management_collection(COL_APPLICATION)
        col.update_one(filter_, update, contains_extra=True, upsert=True)

    def remove_user(self, user_did):
        """ remove all applications of the user did """

        if not user_did:
            return

        filter_ = {
            COL_APPLICATION_USR_DID: user_did,
        }

        col = self.mcli.get_management_collection(COL_APPLICATION)
        col.delete_many(filter_)
