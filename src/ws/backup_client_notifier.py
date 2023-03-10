from flask_socketio import SocketIO

from src.modules.backup.backup_notifier import BackupNotifier


class BackupClientNotifier(BackupNotifier):
    def __init__(self, socketio: SocketIO):
        BackupNotifier.__init__(self)
        self.socketio = socketio

    def on_progress(self, action: str, progress: str):
        self.socketio.emit('backup_state', {'action': action, 'process': progress})
