import json
import os
import pathlib
import subprocess
import time

from flask import Blueprint, request, jsonify
from flask_apscheduler import APScheduler

from hive.util.auth import did_auth
from hive.util.constants import did_tail_part, RCLONE_CONFIG_FILE
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
        did = did_auth()
        if did is None:
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

    def add_drive_to_rclone(self, config_data):
        env_dist = os.environ
        rclone_config = env_dist["HOME"] + RCLONE_CONFIG_FILE
        config_file = pathlib.Path(rclone_config).absolute()

        with open(config_file, 'a') as h_file:
            # Do not change the string format!!!
            lines ='''
[gdrive_%s]
type = drive
client_id = %s
client_secret = %s
scope = %s
token = %s
''' % (config_data["did"], config_data["client_id"], config_data["client_secret"], config_data["scope"], config_data["token"])
            print(lines)
            h_file.writelines(lines)
        return "gdrive_%s" % config_data["did"]




# @scheduler.task(trigger='interval', id='syn_job', hours=1)
# @scheduler.task(trigger='interval', id='syn_job', seconds=20)
# def syn_job():
#     print('rclone syncing')
#     subprocess.call(
#         'rclone sync ./did_file/iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk_drive:elastos',
#         shell=True)
