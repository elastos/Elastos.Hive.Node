import subprocess
import time

from flask import Blueprint, request, jsonify
from flask_apscheduler import APScheduler;

from hive.main.hive_file import HiveFile
from hive.main.hive_mongo import HiveMongo

scheduler = APScheduler()


def init_app(app):
    scheduler.init_app(app)
    scheduler.start()


# @scheduler.task(trigger='interval', id='rclone_sync_job', hours=1)
# @scheduler.task(trigger='interval', id='test_job', seconds=20)
def test_job():
    print('hello world')
    subprocess.call('rclone sync /Users/wanghan/Downloads/rclone test_drive:rclone', shell=True)
