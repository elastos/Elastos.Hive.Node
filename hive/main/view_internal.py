from flask import Blueprint

from hive.main.hive_internal import HiveInternal
from hive.util.constants import INTER_BACKUP_SAVE_FINISH_URL, INTER_BACKUP_RESTORE_FINISH_URL, INTER_BACKUP_TRANSFER_FILES_URL, \
    INTER_BACKUP_UPLOAD_FILE_URL, INTER_BACKUP_MOVE_FILE_URL, INTER_BACKUP_COPY_FILE_URL, INTER_BACKUP_PATCH_HASH_URL, INTER_BACKUP_PATCH_DELTA_URL, \
    INTER_BACKUP_SERVICE_URL

h_internal = HiveInternal()
hive_internal = Blueprint('hive_internal', __name__)


def init_app(app, mode):
    h_internal.init_app(app, mode)
    app.register_blueprint(hive_internal)


@hive_internal.route(INTER_BACKUP_SERVICE_URL, methods=['GET'])
def inter_get_backup_service():
    return h_internal.get_backup_service()


@hive_internal.route(INTER_BACKUP_SAVE_FINISH_URL, methods=['POST'])
def inter_save_finish():
    return h_internal.backup_save_finish()


@hive_internal.route(INTER_BACKUP_RESTORE_FINISH_URL, methods=['POST'])
def inter_restore_finish():
    return h_internal.backup_restore_finish()


@hive_internal.route(INTER_BACKUP_TRANSFER_FILES_URL, methods=['GET'])
def inter_transfer_files():
    return h_internal.get_transfer_files()


@hive_internal.route(INTER_BACKUP_UPLOAD_FILE_URL, methods=['POST'])
def inter_upload():
    return h_internal.upload_file()


@hive_internal.route(INTER_BACKUP_MOVE_FILE_URL, methods=['POST'])
def inter_move():
    return h_internal.move_file()


@hive_internal.route(INTER_BACKUP_COPY_FILE_URL, methods=['POST'])
def inter_copy():
    return h_internal.copy_file()


@hive_internal.route(INTER_BACKUP_PATCH_HASH_URL, methods=['GET'])
def inter_get_patch_hash():
    return h_internal.get_file_hash()


@hive_internal.route(INTER_BACKUP_PATCH_DELTA_URL, methods=['POST'])
def inter_post_patch_delta():
    return h_internal.post_file_delta()
