import _thread
import json
import os
import pathlib
import re
import subprocess
from datetime import datetime
from time import time

from flask import Blueprint, request, jsonify
from flask_apscheduler import APScheduler

from hive.main import view
from hive.util.auth import did_auth
from hive.util.common import did_tail_part, create_full_path_dir
from hive.settings import DID_BASE_DIR, RCLONE_CONFIG_FILE
from hive.util.constants import DID_SYNC_INFO_STATE, DID, DID_SYNC_INFO_DRIVE, APP_ID, DID_SYNC_INFO_TIME, \
    DID_SYNC_INFO_MSG
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import import_mongo_db, export_mongo_db
from hive.util.did_sync import get_did_sync_info, DATA_SYNC_STATE_RUNNING, add_did_sync_info, get_all_did_sync_info, \
    DATA_SYNC_STATE_NONE, DATA_SYNC_STATE_INIT, DATA_SYNC_MSG_INIT_SYNC, update_did_sync_info, \
    DATA_SYNC_MSG_INIT_MONGODB, DATA_SYNC_MSG_SUCCESS, DATA_SYNC_MSG_SYNCING
from hive.util.server_response import response_err, response_ok

scheduler = APScheduler()


class HiveSync:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app
        scheduler.init_app(app)
        scheduler.start()

    def setup_google_drive_rclone(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        access_token = content.get('token', None)
        refresh_token = content.get('refresh_token', None)
        expiry = content.get('expiry', None)
        client_id = content.get('client_id', None)
        client_secret = content.get('client_secret', None)

        token = {
            "access_token": access_token,
            "token_type": "Bearer",
            "refresh_token": refresh_token,
            "expiry": expiry
        }

        config_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "drive",
            "token": json.dumps(token),
            "did": did,
        }

        if HiveSync.is_google_drive_exist(did):
            HiveSync.update_drive_to_rclone(config_data)
        else:
            drive = HiveSync.add_drive_to_rclone(config_data)
            add_did_sync_info(did, time(), drive)

        _thread.start_new_thread(HiveSync.sync_did_data, (did,))

        return response_ok()

    @staticmethod
    def gene_did_google_drive_name(did):
        drive = "gdrive_%s" % did_tail_part(did)
        return drive

    @staticmethod
    def get_did_sync_path(did):
        path = pathlib.Path(DID_BASE_DIR)
        if path.is_absolute():
            path = path / did_tail_part(did)
        else:
            path = path.resolve() / did_tail_part(did)
        return path.resolve()

    @staticmethod
    def find_rclone_config():
        env_dist = os.environ
        rclone_config = env_dist["HOME"] + RCLONE_CONFIG_FILE
        config_file = pathlib.Path(rclone_config).absolute()
        return config_file

    @staticmethod
    def is_app_sync_prepared(did, app_id):
        sync_info = get_did_sync_info(did)
        if (sync_info is None) or (sync_info[DID_SYNC_INFO_STATE] != DATA_SYNC_STATE_RUNNING):
            return False
        else:
            return True

    @staticmethod
    def prepare_did_sync_data(did):
        did_info_list = get_all_did_info_by_did(did)
        for did_info in did_info_list:
            export_mongo_db(did_info[DID], did_info[APP_ID])

    @staticmethod
    def init_did_data(info):
        update_did_sync_info(info[DID], DATA_SYNC_STATE_INIT, DATA_SYNC_MSG_INIT_SYNC, time(),
                             info[DID_SYNC_INFO_DRIVE])
        did_folder = HiveSync.get_did_sync_path(info[DID])
        if not did_folder.exists():
            create_full_path_dir(did_folder)
        line = 'rclone copy %s:elastos_hive_node_data %s' % (info[DID_SYNC_INFO_DRIVE], did_folder.as_posix())
        subprocess.call(line, shell=True)

        update_did_sync_info(info[DID], DATA_SYNC_STATE_INIT, DATA_SYNC_MSG_INIT_MONGODB, time(),
                             info[DID_SYNC_INFO_DRIVE])
        did_info_list = get_all_did_info_by_did(info[DID])
        for did_info in did_info_list:
            import_mongo_db(did_info[DID], did_info[APP_ID])
            view.hive_mongo.init_eve(did_info[DID], did_info[APP_ID])

        update_did_sync_info(info[DID], DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SUCCESS, time(),
                             info[DID_SYNC_INFO_DRIVE])

    @staticmethod
    def sync_did_data(did):
        info = get_did_sync_info(did)
        if info[DID_SYNC_INFO_STATE] == DATA_SYNC_STATE_NONE:
            HiveSync.init_did_data(info)
        elif info[DID_SYNC_INFO_STATE] == DATA_SYNC_STATE_INIT:
            info_new = get_did_sync_info(info[DID])
            # If there is a lone time in init state, we restart it
            if (info_new[DID_SYNC_INFO_TIME] + 12 * 60 * 60) < time():
                HiveSync.init_did_data(info)
        elif info[DID_SYNC_INFO_STATE] == DATA_SYNC_STATE_RUNNING:
            info_new = get_did_sync_info(info[DID])
            if info_new[DID_SYNC_INFO_MSG] == DATA_SYNC_MSG_SYNCING:
                return
            else:
                update_did_sync_info(info[DID], DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SYNCING, time(),
                                     info[DID_SYNC_INFO_DRIVE])
                HiveSync.prepare_did_sync_data(info[DID])
                did_folder = HiveSync.get_did_sync_path(info[DID])
                line = 'rclone sync %s %s:elastos_hive_node_data' % (did_folder.as_posix(), info[DID_SYNC_INFO_DRIVE])
                subprocess.call(line, shell=True)
                update_did_sync_info(info[DID], DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SUCCESS, time(),
                                     info[DID_SYNC_INFO_DRIVE])

    @staticmethod
    def syn_all_drive():
        infos = get_all_did_sync_info()
        for info in infos:
            _thread.start_new_thread(HiveSync.sync_did_data, (info[DID],))

    @staticmethod
    def is_google_drive_exist(did):
        config_file = HiveSync.find_rclone_config()
        if not config_file.exists():
            print("Error: rclone config file do not exist")
            return False

        drive = "[gdrive_%s]" % did_tail_part(did)
        with open(config_file, 'r') as h_file:
            lines = h_file.readlines()
            for line in lines:
                if 0 < line.find(drive):
                    return True
        return False

    @staticmethod
    def update_drive_to_rclone(config_data):
        # Do not change the string format!!!
        drive_name = HiveSync.gene_did_google_drive_name(config_data["did"])
        new_lines = '''
[%s]
type = drive
client_id = %s
client_secret = %s
scope = %s
token = %s
''' % (drive_name,
       config_data["client_id"],
       config_data["client_secret"],
       config_data["scope"],
       config_data["token"])

        config_file = HiveSync.find_rclone_config()
        if not config_file.exists():
            print("Error: rclone config file do not exist")
            return
        file_data = ""
        content_replace = False
        with open(config_file, 'a') as h_file:
            lines = h_file.readlines()
            for line in lines:
                if 0 < line.find(drive_name):
                    content_replace = True
                    file_data += new_lines
                if not content_replace:
                    file_data += line
                else:
                    test = ''.join(line.split())
                    if test == "":
                        content_replace = False
                        file_data += line

        with open(config_file, "w") as h_file:
            h_file.write(file_data)
        return drive_name

    @staticmethod
    def add_drive_to_rclone(config_data):

        drive_name = HiveSync.gene_did_google_drive_name(config_data["did"])

        config_file = HiveSync.find_rclone_config()
        if not config_file.exists():
            print("Error: rclone config file do not exist")
            return

        with open(config_file, 'a') as h_file:
            # Do not change the string format!!!
            lines = '''
[%s]
type = drive
client_id = %s
client_secret = %s
scope = %s
token = %s
    ''' % (drive_name,
           config_data["client_id"],
           config_data["client_secret"],
           config_data["scope"],
           config_data["token"])
            print(lines)
            h_file.writelines(lines)
        return drive_name


@scheduler.task(trigger='interval', id='syn_job', hours=1)
def syn_job():
    print('rclone syncing start:' + str(datetime.now()))
    HiveSync.syn_all_drive()
    print('rclone syncing end:' + str(datetime.now()))
