from pathlib import Path


class Encryption:
    def __init__(self, pk=None):
        self.private_key = pk if pk is not None else self.__generate_private_key()

    def __generate_private_key(self):
        """ raw key """
        pass

    def get_private_key(self) -> str:
        """ return the private key with base58 format. """
        pass

    def encrypt_file(self, src_full_path: Path, dst_full_path: Path):
        pass

    def decrypt_file(self, src_full_path: Path, dst_full_path: Path):
        pass

    @staticmethod
    def encrypt_file_with_curve25519(src_full_path: Path, dst_full_path: Path):
        pass

    @staticmethod
    def decrypt_file_with_curve25519(src_full_path: Path, dst_full_path: Path):
        pass
