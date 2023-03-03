import logging


class BackupNotifier:
    """ Base class for receive some data from backup module. """
    def __init__(self):
        pass

    def on_process(self, action: str, process: str):
        """ notify when backup and restore.
        :param action: backup or restore.
        :param process: str, number by percentage point; 100-based.
        """
        logging.getLogger('BackupNotifier').debug(f'on_process with {action}, {process}')
