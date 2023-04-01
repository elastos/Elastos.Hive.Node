import logging
from datetime import datetime
import bson

from src.modules.database.mongodb_collection import CollectionName, mongodb_collection, MongodbCollection, \
    CollectionGenericField
from src.modules.database.mongodb_client import mcli


class AppState:
    NORMAL = 'normal'
    # REMOVED = 'removed'


@mongodb_collection(CollectionName.APPLICATION, is_management=True, is_internal=True)
class CollectionApplication(MongodbCollection):
    """ represents the application on the vault. """

    # Contain extra two fields: created, modified.
    USR_DID = CollectionGenericField.USR_DID
    APP_DID = CollectionGenericField.APP_DID
    DATABASE_NAME = 'database_name'
    ACCESS_COUNT = 'access_count'  # app data access times.
    ACCESS_AMOUNT = 'access_amount'  # app data access amount (bytes).
    ACCESS_LAST_TIME = 'access_last_time'  # for app data.
    STATE = CollectionGenericField.STATE

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=True)

    def get_user_count(self):
        return len(self.distinct(self.USR_DID))

    def get_apps(self, user_did) -> list:
        """ get all application information by user did"""

        if not user_did:
            return []

        return self.find_many(self._get_filter(user_did))

    def get_app(self, user_did: str, app_did: str):
        if not user_did or not app_did:
            return None

        return self.find_one(self._get_filter(user_did, app_did))

    def get_app_dids(self, user_did) -> list:
        """ get all application DIDs of the user did """
        return list(map(lambda d: d[self.APP_DID], self.get_apps(user_did)))

    def get_app_database_names(self, user_did) -> list:
        """ get all database names of the user did """
        return list(map(lambda d: d[self.DATABASE_NAME], self.get_apps(user_did)))

    def save_app(self, user_did, app_did):
        """ add the relation of user did and app did to collection if not exists.

        :param user_did can not be None
        :param app_did application did
        """

        if not user_did or not app_did:
            logging.getLogger('CollectionApplication').error(f'Skip adding invalid user_did({user_did}) or app_did({app_did})')
            return

        update = {'$setOnInsert': {
            self.DATABASE_NAME: mcli.get_user_database_name(user_did, app_did),
            self.STATE: AppState.NORMAL}}

        self.update_one(self._get_filter(user_did, app_did), update, contains_extra=True, upsert=True)

    def update_app_access(self, user_did, app_did, access_count: int = 0, data_amount: int = 0):
        """ Update access information for the user's application. """

        if not user_did or not app_did:
            logging.getLogger('CollectionApplication').error(f'Skip update_app_access() by invalid user_did({user_did}) or app_did({app_did})')
            return

        update = {'$set': {self.ACCESS_LAST_TIME: int(datetime.now().timestamp())}}
        inc = {}
        if access_count > 0:
            inc[self.ACCESS_COUNT] = access_count
        if data_amount > 0:
            inc[self.ACCESS_AMOUNT] = bson.Int64(data_amount)
        if inc:
            update['$inc'] = inc

        self.update_one(self._get_filter(user_did, app_did), update, contains_extra=True, upsert=False)

    def remove_user(self, user_did):
        """ remove all applications of the user did """

        if not user_did:
            return

        self.delete_many(self._get_filter(user_did))

    def remove_user_app(self, user_did, app_did):
        if not user_did or not app_did:
            return

        self.delete_one(self._get_filter(user_did, app_did))

    def _get_filter(self, user_did, app_did=None):
        filter_ = {self.USR_DID: user_did}
        if app_did is not None:
            filter_[self.APP_DID] = app_did
        return filter_
