import logging

from flask_socketio import SocketIO

from src.modules.backup.backup_client import bc
from src.ws.backup_client_notifier import BackupClientNotifier


def init(socketio: SocketIO):
    @socketio.on('backup_state')
    def handle_message(data):
        logging.getLogger('ws.backup').debug(f'received message: {data}')

    bc.set_notifier(BackupClientNotifier(socketio))
