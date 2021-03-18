from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from hive.settings import hive_setting


class FtpServer:
    def __init__(self, path, port):
        self.authorizer = DummyAuthorizer()
        self.handler = FTPHandler
        self.handler.authorizer = self.authorizer
        self.handler.banner = "hive backup ftp ready."
        self.handler.masquerade_address = hive_setting.BACKUP_FTP_MASQUERADE_ADDRESS
        self.handler.passive_ports = range(hive_setting.BACKUP_FTP_PASSIVE_PORTS_START,
                                           hive_setting.BACKUP_FTP_PASSIVE_PORTS_END)
        self.address = ('', port)
        self.server = FTPServer(self.address, self.handler)
        self.server.max_cons = 256
        self.server.max_cons_per_ip = 5

    def run(self):
        self.server.serve_forever()

    def add_user(self, user, passwd, loc, privi):
        self.authorizer.add_user(str(user), str(passwd), str(loc), perm=str(privi))

    def remove_user(self, user):
        self.authorizer.remove_user(str(user))
