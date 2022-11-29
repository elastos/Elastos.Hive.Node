from flask_socketio import SocketIO, send, disconnect

from src import HiveException, InternalServerErrorException
from src.utils.auth_token import parse_websocket_token
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import get_dict, RequestData


class WebSocketHandler:
    def __init__(self, content):
        self.content = content

    def handle(self):
        ...


_socketio = SocketIO()  # port is same as node.
_handlers: dict[str: WebSocketHandler] = {}


def init_websocket(app, handlers):
    """
    :param app: Flask app
    :param handlers: Handlers for receiving messages.
        [{
            "method": "<method>",
            "handler": "<handler class with 'handle()' method>"
        }]
    """
    _socketio.init_app(app)
    global _handlers
    _handlers = handlers


def socket_request(f):
    """ A decorator which makes the endpoint support the stream response """
    def wrapper(json):
        try:
            f(json)
        except HiveException as e:
            send(e.get_error_str())
        except Exception as e:
            send(InternalServerErrorException(f'Error: {e}').get_error_str())
    return wrapper


@_socketio.on('json')
@socket_request
def handle_json(json):
    """ The json message format:
    {
        "method": "<pubsub_message>",
        "token": "<token_str>",
        "content": {
        }
    }

    """
    body = RequestData(**get_dict(json))
    method, token, content = body.get('method', str), body.get('token', str), body.get('content', dict)
    parse_websocket_token(token)

    handler_cls = _handlers.get(method)
    if not handler_cls:
        raise InvalidParameterException('Invalid method.')

    handler: WebSocketHandler = handler_cls(content)
    if handler.handle():
        disconnect()
