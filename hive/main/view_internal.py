from flask import Blueprint

from hive.main.hive_internal import HiveInternal
from hive.util.constants import INTER_BACKUP_SAVE_FINISH_URL, INTER_BACKUP_RESTORE_FINISH_URL, \
    INTER_BACKUP_FILE_LIST_URL, \
    INTER_BACKUP_FILE_URL, INTER_BACKUP_MOVE_FILE_URL, INTER_BACKUP_COPY_FILE_URL, INTER_BACKUP_PATCH_HASH_URL, \
    INTER_BACKUP_PATCH_DELTA_URL, INTER_BACKUP_SERVICE_URL

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


@hive_internal.route(INTER_BACKUP_FILE_LIST_URL, methods=['GET'])
def inter_get_backup_files():
    return h_internal.get_backup_files()


@hive_internal.route(INTER_BACKUP_FILE_URL + "/<path:file_name>", methods=['PUT'])
def inter_put_file(file_name):
    return h_internal.put_file(file_name)


@hive_internal.route(INTER_BACKUP_FILE_URL, methods=['GET'])
def inter_get_file():
    return h_internal.get_file()


@hive_internal.route(INTER_BACKUP_FILE_URL, methods=['POST'])
def inter_delete_file():
    return h_internal.delete_file()


@hive_internal.route(INTER_BACKUP_MOVE_FILE_URL, methods=['POST'])
def inter_move():
    return h_internal.move_file(is_copy=False)


@hive_internal.route(INTER_BACKUP_COPY_FILE_URL, methods=['POST'])
def inter_copy():
    return h_internal.move_file(is_copy=True)


@hive_internal.route(INTER_BACKUP_PATCH_HASH_URL, methods=['GET'])
def inter_get_patch_hash():
    return h_internal.get_file_patch_hash()


@hive_internal.route(INTER_BACKUP_PATCH_DELTA_URL, methods=['POST'])
def inter_patch_delta():
    return h_internal.patch_file_delta()
