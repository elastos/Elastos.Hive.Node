from flask import Blueprint

from hive.main.hive_backup import HiveBackup
from hive.util.constants import INTER_BACKUP_FTP_START_URL, INTER_BACKUP_FTP_END_URL, INTER_BACKUP_SAVE_URL, \
    INTER_BACKUP_RESTORE_URL

h_backup = HiveBackup()
hive_backup = Blueprint('hive_backup', __name__)


def init_app(app, mode):
    h_backup.init_app(app, mode)
    app.register_blueprint(hive_backup)


@hive_backup.route('/api/v1/backup/save_to_google_drive', methods=['POST'])
def save_to_google_drive():
    return h_backup.save_to_google_drive()


@hive_backup.route('/api/v1/backup/restore_from_google_drive', methods=['POST'])
def restore_from_google_drive():
    return h_backup.restore_from_google_drive()


@hive_backup.route('/api/v1/backup/state', methods=['GET'])
def get_sync_state():
    return h_backup.get_sync_state()


@hive_backup.route('/api/v1/backup/save_to_node', methods=['POST'])
def save_to_node():
    return h_backup.save_to_hive_node()


@hive_backup.route('/api/v1/backup/restore_from_node', methods=['POST'])
def restore_from_node():
    return h_backup.restore_from_hive_node()


@hive_backup.route("/api/v1/backup/activate_to_vault", methods=['POST'])
def backup_to_vault():
    return h_backup.backup_to_vault()


@hive_backup.route(INTER_BACKUP_SAVE_URL, methods=['POST'])
def inter_backup_save():
    return h_backup.inter_backup_save()


@hive_backup.route(INTER_BACKUP_RESTORE_URL, methods=['POST'])
def inter_backup_restore():
    return h_backup.inter_backup_restore()


@hive_backup.route(INTER_BACKUP_FTP_START_URL, methods=['POST'])
def inter_ftp_start():
    return h_backup.inter_backup_ftp_start()


@hive_backup.route(INTER_BACKUP_FTP_END_URL, methods=['POST'])
def inter_ftp_end():
    return h_backup.inter_backup_ftp_end()
