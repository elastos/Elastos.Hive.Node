from flask import Blueprint

from hive.main.hive_backup import HiveBackup
from hive.util.constants import INTER_BACKUP_START_URL, INTER_BACKUP_END_URL, INTER_BACKUP_TO_VAULT_URL

h_backup = HiveBackup()
hive_backup = Blueprint('hive_backup', __name__)


def init_app(app, mode):
    h_backup.init_app(app, mode)
    app.register_blueprint(hive_backup)


@hive_backup.route('/api/v1/backup/save/to/google_drive', methods=['POST'])
def save_to_google_drive():
    return h_backup.save_to_google_drive()


@hive_backup.route('/api/v1/backup/restore/from/google_drive', methods=['POST'])
def restore_from_google_drive():
    return h_backup.restore_from_google_drive()


@hive_backup.route('/api/v1/backup/state', methods=['GET'])
def get_sync_state():
    return h_backup.get_sync_state()


@hive_backup.route('/api/v1/backup/save/to/node', methods=['POST'])
def save_to_node():
    return h_backup.save_to_hive_node()


@hive_backup.route('/api/v1/backup/restore/from/node', methods=['POST'])
def restore_from_node():
    return h_backup.restore_from_hive_node()


@hive_backup.route('/api/v1/backup/immigrate/node', methods=['POST'])
def immigrate_node():
    return h_backup.immigrate_node()


@hive_backup.route(INTER_BACKUP_START_URL, methods=['POST'])
def backup_communication_start():
    return h_backup.backup_communication_start()


@hive_backup.route(INTER_BACKUP_END_URL, methods=['POST'])
def backup_communication_end():
    return h_backup.backup_communication_end()

@hive_backup.route(INTER_BACKUP_TO_VAULT_URL, methods=['POST'])
def backup_to_vault():
    return h_backup.backup_to_vault()
