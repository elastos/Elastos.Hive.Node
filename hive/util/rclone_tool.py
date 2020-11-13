import json
import logging
import os
import pathlib

from hive.settings import RCLONE_CONFIG_FILE_DIR


class RcloneTool:
    @staticmethod
    def get_config_data(self, content, did):
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
    def find_rclone_config_file(file_name):
        config_file = pathlib.Path(RCLONE_CONFIG_FILE_DIR).absolute() / file_name
        if config_file.exists():
            return True
        else:
            return False

    @staticmethod
    def create_rclone_config_file(drive_name, config_data):
        config_file = pathlib.Path(RCLONE_CONFIG_FILE_DIR).absolute() / drive_name
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
        config_file = pathlib.Path(RCLONE_CONFIG_FILE_DIR).absolute() / drive_name
        if config_file.exists():
            config_file.unlink()
