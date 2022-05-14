from src.utils.db_client import cli
from src.utils_v1.constants import DID_INFO_DB_NAME


class MongodbCollection:
    """ all collection wrapper """
    def __init__(self, col):
        self.col = col


class MongodbClient:
    """ Used to connect mongodb and is a helper class for all mongo database operation.
    This class is used to replace class `src.utils.db_client.DatabaseClient`.
    """

    def __init__(self):
        self.cli = cli

    def get_mgr_collection(self, col_name, create_on_absence=False) -> MongodbCollection:
        col = self.cli.get_origin_collection(DID_INFO_DB_NAME, col_name, create_on_absence=create_on_absence)
        return MongodbCollection(col)

    def get_usr_collection(self, user_did: str, app_did: str, col_name, create_on_absence=False) -> MongodbCollection:
        col = self.cli.get_user_collection(user_did, app_did, col_name, create_on_absence=create_on_absence)
        return MongodbCollection(col)

    def get_vault_info(self, user_did: str):
        self.cli.get_vault_service(user_did)
