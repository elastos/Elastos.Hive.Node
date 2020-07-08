import json
import os
import pathlib
import re
import subprocess
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_apscheduler import APScheduler

from hive.util.auth import did_auth
from hive.util.constants import did_tail_part, RCLONE_CONFIG_FILE, DID_FILE_DIR
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
            "scope": "drive.file",
            "token": json.dumps(token),
            "did": did_tail_part(did)
        }

        drive = self.add_drive_to_rclone(config_data)
        data = {"drive": drive}
        return response_ok(data)

    @staticmethod
    def find_rclone_config():
        env_dist = os.environ
        rclone_config = env_dist["HOME"] + RCLONE_CONFIG_FILE
        config_file = pathlib.Path(rclone_config).absolute()
        return config_file

    @staticmethod
    def get_all_rclone_config_drive():
        config_file = HiveSync.find_rclone_config()
        drives = list()
        with open(config_file) as h_file:
            for l in h_file.readlines():
                l = l.strip("\n")
                line = re.match(r"^\[([^\[\]]*)\]$", l)
                if line is not None:
                    drives.append(line.group().strip("[]"))
        return drives

    @staticmethod
    def get_all_did_dirs():
        did_dirs = list()
        file_dirs = pathlib.Path(DID_FILE_DIR).absolute()
        if not file_dirs.exists():
            return
        for dirs in file_dirs.iterdir():
            if dirs.is_dir():
                did_dirs.append(dirs.name)
        return did_dirs

    @staticmethod
    def get_all_syn_drive():
        did_dirs = HiveSync.get_all_did_dirs()
        drives = HiveSync.get_all_rclone_config_drive()
        syn = dict()
        for drive in drives:
            for did in did_dirs:
                if drive.find(did) != -1:
                    syn[did] = drive
        return syn

    def add_drive_to_rclone(self, config_data):
        config_file = self.find_rclone_config()

        with open(config_file, 'a') as h_file:
            # Do not change the string format!!!
            lines = '''
[gdrive_%s]
type = drive
client_id = %s
client_secret = %s
scope = %s
token = %s
''' % (config_data["did"], config_data["client_id"], config_data["client_secret"], config_data["scope"],
       config_data["token"])
            print(lines)
            h_file.writelines(lines)
        return "gdrive_%s" % config_data["did"]


# if __name__ == '__main__':
#     # HiveSync.get_all_rclone_config_drive()
#     syn = HiveSync.get_all_syn_drive()
#     for key, value in syn.items():
#         files = pathlib.Path(DID_FILE_DIR).absolute() / key
#         line = 'rclone sync %s %s:elastos' % (files.as_posix(), value)
#         print(line)


# @scheduler.task(trigger='interval', id='syn_job', hours=1)
# @scheduler.task(trigger='interval', id='syn_job', seconds=10)
def syn_job():
    print('rclone syncing start:' + str(datetime.now()))
    syn_dirs = HiveSync.get_all_syn_drive()
    for key, value in syn_dirs.items():
        files = pathlib.Path(DID_FILE_DIR).absolute() / key
        line = 'rclone sync %s %s:elastos' % (files.as_posix(), value)
        print(line)
        subprocess.call(line, shell=True)
        # subprocess.Popen(line, shell=True)
    print('rclone syncing end:' + str(datetime.now()))
