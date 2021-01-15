import json
import logging
import os
import pathlib

from hive.settings import hive_setting
from hive.util.common import create_full_path_dir


class RcloneTool:
    @staticmethod
    def get_config_data(content, did):
        access_token = content.get('token')
        refresh_token = content.get('refresh_token')
        expiry = content.get('expiry')
        client_id = content.get('client_id')
        client_secret = content.get('client_secret')

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
        return config_data

    @staticmethod
    def find_rclone_config_file(drive_name):
        config_file = pathlib.Path(hive_setting.RCLONE_CONFIG_FILE_DIR).absolute() / drive_name
        if config_file.exists():
            return config_file
        else:
            return None

    @staticmethod
    def create_rclone_config_file(drive_name, config_data):
        path = pathlib.Path(hive_setting.RCLONE_CONFIG_FILE_DIR).absolute()
        if not path.exists():
            path.mkdir(exist_ok=True, parents=True)

        config_file = path / drive_name

        if config_file.exists():
            config_file.unlink()

        with open(config_file, 'w') as h_file:
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

    @staticmethod
    def remove_rclone_config_file(drive_name):
        config_file = pathlib.Path(hive_setting.RCLONE_CONFIG_FILE_DIR).absolute() / drive_name
        if config_file.exists():
            config_file.unlink()
