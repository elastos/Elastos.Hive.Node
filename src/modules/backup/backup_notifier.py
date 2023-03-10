import logging


class BackupNotifier:
    """ Base class for receive some data from backup module. """
    def __init__(self):
        pass

    def on_progress(self, action: str, progress: str):
        """ notify when backup and restore.
        :param action: backup or restore.
        :param progress: str, number by percentage point; 100-based.
        """
        logging.getLogger('BackupNotifier').debug(f'on_progress with {action}, {progress}')
