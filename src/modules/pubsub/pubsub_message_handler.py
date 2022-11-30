import json
import time
from datetime import datetime

from flask import g

from src.modules.pubsub.pubsub_service import PubSubMessage


class PubSubMessageHandler:
    def __init__(self, ws, content):
        self.ws = ws
        self.content = content
        self.message = PubSubMessage()
        self.quit = False

    def handle(self):
        """ Every notification message format:
        {
            "collections": {
                "<collection_name>": 30
            }
        }
        """

        user_did, app_did = g.usr_did, g.app_did

        messages = self.message.get_all_by_user(user_did, app_did, raw=False)
        if not messages:
            return True

        while not self.quit:
            for msg in messages:
                cur_t = int(datetime.now().timestamp())
                if msg.get_next() == -1 or msg.get_next() < cur_t:
                    items = self.message.get_result(msg, cur_t)
                    if items:
                        self.ws.send(json.dumps({'collections': items}))
                    msg.update_next(cur_t)

                time.sleep(1)

        return False
