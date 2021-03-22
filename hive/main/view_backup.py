from flask import Blueprint

from hive.main.hive_backup import HiveBackup

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
