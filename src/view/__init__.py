# -*- coding: utf-8 -*-
import logging

from flask_restful import Api

from src import hive_setting
from src.utils.consts import URL_SIGN_IN, URL_AUTH, URL_BACKUP_AUTH, URL_SERVER_INTERNAL_BACKUP, URL_SERVER_INTERNAL_RESTORE, URL_SERVER_INTERNAL_STATE
from src.view import about, auth, subscription, database, files, scripting, payment, backup, provider


def init_app(api: Api):
    logging.getLogger('v2_init').info('enter init_app')

    # auth service
    api.add_resource(auth.SignIn, URL_SIGN_IN, endpoint='v2_auth.sign_in')
    api.add_resource(auth.Auth, URL_AUTH, endpoint='v2_auth.auth')
    api.add_resource(auth.BackupAuth, URL_BACKUP_AUTH, endpoint='v2_auth.backup_auth')

    # subscription service
    api.add_resource(subscription.VaultInfo, '/subscription/vault', endpoint='subscription.vault_info')
    api.add_resource(subscription.VaultAppStates, '/subscription/vault/app_stats', endpoint='subscription.vault_app_states')
    api.add_resource(subscription.VaultPricePlan, '/subscription/pricing_plan', endpoint='subscription.vault_price_plan')
    api.add_resource(subscription.VaultActivateDeactivate, '/subscription/vault', endpoint='subscription.vault_activate_deactivate')
    api.add_resource(subscription.VaultSubscribe, '/subscription/vault', endpoint='subscription.vault_subscribe')
    api.add_resource(subscription.VaultUnsubscribe, '/subscription/vault', endpoint='subscription.vault_unsubscribe')
    api.add_resource(subscription.BackupInfo, '/subscription/backup', endpoint='subscription.backup_info')
    api.add_resource(subscription.BackupActivateDeactivate, '/subscription/backup', endpoint='subscription.backup_activate_deactivate')
    api.add_resource(subscription.BackupSubscribe, '/subscription/backup', endpoint='subscription.backup_subscribe')
    api.add_resource(subscription.BackupUnsubscribe, '/subscription/backup', endpoint='subscription.backup_unsubscribe')

    # database service
    api.add_resource(database.CreateCollection, '/vault/db/collections/<collection_name>', endpoint='database.create_collection')
    api.add_resource(database.DeleteCollection, '/vault/db/<collection_name>', endpoint='database.delete_collection')
    api.add_resource(database.InsertOrCount, '/vault/db/collection/<collection_name>', endpoint='database.insert_or_count')
    api.add_resource(database.Update, '/vault/db/collection/<collection_name>', endpoint='database.update')
    api.add_resource(database.Delete, '/vault/db/collection/<collection_name>', endpoint='database.delete')
    api.add_resource(database.Find, '/vault/db/<collection_name>', endpoint='database.find')
    api.add_resource(database.Query, '/vault/db/query', endpoint='database.query')

    # files service
    api.add_resource(files.ReadingOperation, '/vault/files/<folder_path:path>', endpoint='files.reading_operation')
    api.add_resource(files.WritingOperation, '/vault/files/<path:path>', endpoint='files.writing_operation')
    api.add_resource(files.MoveFile, '/vault/files/<path:path>', endpoint='files.move_file')
    api.add_resource(files.DeleteFile, '/vault/files/<path:path>', endpoint='files.delete_file')

    # scripting service
    api.add_resource(scripting.RegisterScript, '/vault/scripting/<script_name>', endpoint='scripting.register_script')
    api.add_resource(scripting.CallScript, '/vault/scripting/<script_name>', endpoint='scripting.call_script')
    api.add_resource(scripting.CallScriptUrl, '/vault/scripting/<script_name>/<context_str>/<params>', endpoint='scripting.call_script_url')
    api.add_resource(scripting.UploadFile, '/vault/scripting/stream/<transaction_id>', endpoint='scripting.upload_file')
    api.add_resource(scripting.DownloadFile, '/vault/scripting/stream/<transaction_id>', endpoint='scripting.download_file')
    api.add_resource(scripting.DeleteScript, '/vault/scripting/<script_name>', endpoint='scripting.delete_script')

    # backup service
    api.add_resource(backup.State, '/vault/content', endpoint='backup.state')
    api.add_resource(backup.BackupRestore, '/vault/content', endpoint='backup.backup_restore')
    api.add_resource(backup.ServerPromotion, '/backup/promotion', endpoint='backup.server_promotion')
    api.add_resource(backup.ServerInternalBackup, URL_SERVER_INTERNAL_BACKUP, endpoint='backup.server_internal_backup')
    api.add_resource(backup.ServerInternalState, URL_SERVER_INTERNAL_STATE, endpoint='backup.server_internal_state')
    api.add_resource(backup.ServerInternalRestore, URL_SERVER_INTERNAL_RESTORE, endpoint='backup.server_internal_restore')

    # provider service
    api.add_resource(provider.Vaults, '/provider/vaults', endpoint='provider.vaults')
    api.add_resource(provider.Backups, '/provider/backups', endpoint='provider.backups')
    api.add_resource(provider.FilledOrders, '/provider/filled_orders', endpoint='provider.filled_orders')

    # about service
    # INFO: one class with two lines for the documentation to hide '/about', so don't combine them.
    api.add_resource(about.Version, '/node/version', endpoint='node.version')
    api.add_resource(about.Version, '/about/version', endpoint='about.version')
    api.add_resource(about.CommitId, '/node/commit_id', endpoint='node.commit_id')
    api.add_resource(about.CommitId, '/about/commit_id', endpoint='about.commit_id')
    api.add_resource(about.NodeInfo, '/node/info', endpoint='node.info')

    if hive_setting.PAYMENT_ENABLED:
        # payment service
        api.add_resource(payment.Version, '/payment/version', endpoint='payment.version')
        api.add_resource(payment.PlaceOrder, '/payment/order', endpoint='payment.place_order')
        api.add_resource(payment.SettleOrder, '/payment/order/<order_id>', endpoint='payment.settle_order')
        api.add_resource(payment.Orders, '/payment/order', endpoint='payment.orders')
        api.add_resource(payment.Receipts, '/payment/receipt', endpoint='payment.receipts')

    logging.getLogger('v2_init').info('leave init_app')
