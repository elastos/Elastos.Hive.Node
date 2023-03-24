from enum import Enum
import jwt
from bson import ObjectId

from src import hive_setting
from src.modules.database.mongodb_client import mcli
from src.modules.database.mongodb_collection import mongodb_collection, MongodbCollection, CollectionName
from src.utils.http_exception import InvalidParameterException


class ActionType(Enum):
    UPLOAD = 'upload',
    DOWNLOAD = 'download'


@mongodb_collection(CollectionName.SCRIPTS_TRANSACTION, is_management=False, is_internal=True)
class CollectionScriptsTransaction(MongodbCollection):
    """ This class keeps script transaction info. when doing upload and download by scripts. """

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=False)

    def create_script_transaction_id(self, file_path: str, action_type: ActionType, anonymous: bool):
        result = self.insert_one({
            "document": {
                "file_name": file_path,
                "fileapi_type": str(action_type)
            },
            'anonymous': anonymous
        })

        return jwt.encode({
                "row_id": result['inserted_id'],
                "target_did": self.user_did,
                "target_app_did": self.app_did,
            }, hive_setting.PASSWORD, algorithm='HS256')

    @staticmethod
    def parse_script_transaction_id(transaction_id):
        row_id, target_did, target_app_did = CollectionScriptsTransaction.parse_transaction_id(transaction_id)

        trans = mcli.get_col(CollectionScriptsTransaction, user_did=target_did, app_did=target_app_did).find_one({"_id": ObjectId(row_id)})
        if not trans:
            raise InvalidParameterException('Invalid transaction id: can not found transaction')

        return row_id, target_did, target_app_did, trans

    def delete_script_transaction(self, trans_row_id):
        self.delete_one({"_id": ObjectId(trans_row_id)})

    @staticmethod
    def parse_transaction_id(transaction_id):
        try:
            trans = jwt.decode(transaction_id, hive_setting.PASSWORD, algorithms=['HS256'])
        except Exception as e:
            raise InvalidParameterException(f"Invalid transaction id '{transaction_id}'")

        if not trans or not isinstance(trans, dict):
            raise InvalidParameterException(f"Invalid transaction id '{transaction_id}', {trans}.")

        row_id, target_did, target_app_did = trans.get('row_id', None), trans.get('target_did', None), trans.get('target_app_did', None)
        if not row_id or not target_did or not target_app_did:
            raise InvalidParameterException(f"Invalid transaction id '{transaction_id}': {[row_id, target_did, target_app_did]}.")

        return row_id, target_did, target_app_did
