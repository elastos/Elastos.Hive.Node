from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer



# def create_backup_ftp():
#     # Instantiate a dummy authorizer for managing 'virtual' users
#     authorizer = DummyAuthorizer()
#
#     # Define a new user having full r/w permissions and a read-only
#     # anonymous user
#     # authorizer.add_user('user', '12345', '.', perm='elradfmwMT')
#     authorizer.add_user(
#         'user',
#         '12345',
#         '.',
#         perm='lradfmwMT')
#     authorizer.add_anonymous(os.getcwd())
#
#     handler = FTPHandler
#     handler.authorizer = authorizer
#
#     handler.banner = "hive backup ftp ready."
#     address = ('', 2121)
#     server = FTPServer(address, handler)
#     server.max_cons = 256
#     server.max_cons_per_ip = 5
#     server.serve_forever()


class FtpServer:
    def __init__(self, path, port):
        self.authorizer = DummyAuthorizer()
        self.handler = FTPHandler
        self.handler.authorizer = self.authorizer
        self.handler.banner = "hive backup ftp ready."
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
