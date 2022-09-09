from pathlib import Path

import base58
import nacl.secret
import nacl.utils

from src import hive_setting
from src.modules.auth import auth
from src.utils.did.did_wrapper import CipherDecryptionStream


class Encryption:
    TRUNK_SIZE = 4096

    def __init__(self, pk: str = None, nonce: str = None):
        self.private_key = base58.b58decode(pk).decode('utf8') \
            if pk is not None else nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        self.nonce = base58.b58decode(nonce).decode('utf8') \
            if nonce is not None else nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        self.box = nacl.secret.SecretBox(self.private_key)

    def get_private_key(self):
        """ return the private key with base58 format. """
        return base58.b58encode(self.private_key).decode('utf8'), base58.b58encode(self.nonce).decode('utf8')

    def encrypt_file(self, src_full_path: Path) -> Path:
        dst_full_path = src_full_path / '.encryption'
        with open(src_full_path.as_posix(), 'rb') as f:
            data = f.read()
        cipher_msg = self.box.encrypt(data, self.nonce)
        with open(dst_full_path.as_posix(), 'rw') as f:
            f.write(cipher_msg.ciphertext)
        return dst_full_path

    def decrypt_file(self, src_full_path: Path):
        dst_full_path = src_full_path / '.decryption'
        with open(src_full_path.as_posix(), 'rb') as f:
            data = f.read()
        plain_data = self.box.decrypt(data, self.nonce)
        with open(dst_full_path.as_posix(), 'rw') as f:
            f.write(plain_data)
        return dst_full_path

    @staticmethod
    def __get_cipher(other_side_public_key: str, is_server):
        auth_ = auth.Auth()
        doc = auth_.doc
        cipher = doc.create_curve25519_cipher(auth_.did_str, 3, hive_setting.PASSWORD, is_server)
        cipher.set_other_side_public_key(other_side_public_key)
        return cipher

    @staticmethod
    def encrypt_file_with_curve25519(src_full_path: Path, other_side_public_key: str, is_server: bool) -> Path:
        dst_full_path = src_full_path / '.encryption.curve25519'
        stream = Encryption.__get_cipher(other_side_public_key, is_server).create_encryption_stream()
        total_size = src_full_path.stat().st_size
        remain = total_size
        with open(src_full_path, 'rb') as sf:
            with open(dst_full_path, 'wb') as bf:
                while remain > 0:
                    data = sf.read(Encryption.TRUNK_SIZE)
                    is_final = remain - len(data) <= 0
                    cipher_data = stream.push(data, is_final)
                    bf.write(cipher_data)
                    remain -= len(data)
        return dst_full_path

    @staticmethod
    def decrypt_file_with_curve25519(src_full_path: Path, other_side_public_key: str, is_server: bool) -> Path:
        dst_full_path = src_full_path / '.decryption.curve25519'
        stream = Encryption.__get_cipher(other_side_public_key, is_server).create_decryption_stream()
        total_size = src_full_path.stat().st_size
        remain = total_size
        with open(src_full_path, 'rb') as sf:
            with open(dst_full_path, 'wb') as bf:
                while remain > 0:
                    data = sf.read(Encryption.TRUNK_SIZE + CipherDecryptionStream.extra_encryption_size())
                    plain_data = stream.pull(data)
                    bf.write(plain_data)
                    remain -= len(data)
        return dst_full_path
