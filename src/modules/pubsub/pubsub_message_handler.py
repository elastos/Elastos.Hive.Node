import json

from flask_login import current_user
from flask_socketio import send

from src.utils.websocket import WebSocketHandler
from src.modules.pubsub.pubsub_service import PubSubMessage


class PubSubMessageHandler(WebSocketHandler):
    def __init__(self, content):
        super().__init__(content)
        self.message = PubSubMessage()

    def handle(self):
        """ Every notification message format:
        {
            "collections": {
                "<collection_name>": 30
            }
        }
        """

        user_did, app_did = current_user().user_did, current_user().app_did

        messages = self.message.get_all_by_user(user_did, app_did)
        if not messages:
            return True

        for msg in messages:
            send(json.dumps(self.message.get_result(msg)))

        return False
