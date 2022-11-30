import json
from json import JSONDecodeError

from flask_sock import Sock

from src.utils.auth_token import parse_websocket_token
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import RequestData
from src.modules.pubsub.pubsub_message_handler import PubSubMessageHandler

sock: Sock = Sock()


def init_websocket(app):
    sock.init_app(app)


@sock.route('/ws/echo')
def echo(ws):
    while True:
        data = ws.receive()
        ws.send(data)


@sock.route('/ws/pubsub/message')
def pubsub_message(ws):
    """ Request:
    {
        "token": "<token_str>"
    }
    """

    data = ws.receive()
    try:
        content = json.loads(data)
        if not isinstance(content, dict):
            ws.send(InvalidParameterException('Invalid message.').get_error_str())

        token = RequestData(**content).get('token', str)
        parse_websocket_token(token)
    except JSONDecodeError as e:
        ws.send(InvalidParameterException('Invalid message').get_error_str())
        return

    PubSubMessageHandler(ws, content).handle()

    ws.close()
