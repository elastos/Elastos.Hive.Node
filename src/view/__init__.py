# -*- coding: utf-8 -*-
from hive.settings import hive_setting
from src.view import scripting, subscription, files, database, auth, backup


URL_DID_SIGN_IN = '/api/v2/did/signin'
URL_DID_AUTH = '/api/v2/did/auth'
URL_DID_BACKUP_AUTH = '/api/v2/did/backup_auth'
URL_BACKUP_SERVICE = '/api/v2/internal/backup/service'
URL_BACKUP_FINISH = '/api/v2/internal/backup/finish'
URL_BACKUP_FILES = '/api/v2/internal/backup/files'
URL_BACKUP_FILE = '/api/v2/internal/backup/file'
URL_BACKUP_PATCH_HASH = '/api/v2/internal/backup/patch_hash'
URL_BACKUP_PATCH_FILE = '/api/v2/internal/backup/patch_file'
URL_RESTORE_FINISH = '/api/v2/internal/restore/finish'


def init_app(app, mode):
    auth.init_app(app, hive_setting)
    subscription.init_app(app, hive_setting)
    backup.init_app(app, hive_setting)
    scripting.init_app(app, hive_setting)
    files.init_app(app, hive_setting)
    database.init_app(app, hive_setting)
