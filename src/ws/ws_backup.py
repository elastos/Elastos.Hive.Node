import logging

from flask_socketio import SocketIO


def init(socketio: SocketIO):
    @socketio.on('backup_state')
    def handle_message(data):
        logging.getLogger('ws.backup').debug(f'received message: {data}')
