from pymongo import MongoClient

from hive.settings import hive_setting
from hive.util.constants import DID_INFO_REGISTER_COL, DID_INFO_DB_NAME, DID
from hive.util.payment.payment_config import PaymentConfig
from hive.util.payment.vault_service_manage import get_vault_service, setup_vault_service


def create_vault_of_did(did):
    service = get_vault_service(did)
    if service:
        return

    free_info = PaymentConfig.get_free_vault_info()

    setup_vault_service(did, free_info["maxStorage"], free_info["serviceDays"])


def create_all_vault():
    connection = MongoClient(host=hive_setting.MONGO_HOST, port=hive_setting.MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    infos = col.find()
    for did_info in infos:
        if DID in did_info:
            create_vault_of_did(did_info[DID])


if __name__ == '__main__':
    create_all_vault()
