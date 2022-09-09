from pathlib import Path

import base58
import nacl.secret
import nacl.utils

from src import hive_setting
from src.modules.auth import auth
from src.utils.did.did_wrapper import CipherDecryptionStream
from src.utils.http_exception import BadRequestException


class Encryption:
    TRUNK_SIZE = 4096

    def __init__(self, pk: str = None, nonce: str = None):
        self.private_key = base58.b58decode(bytes(pk, 'utf8')) \
            if pk is not None else nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        self.nonce = base58.b58decode(bytes(nonce, 'utf8')) \
            if nonce is not None else nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        self.box = nacl.secret.SecretBox(self.private_key)

    def get_private_key(self):
        """ return the private key with base58 format. """
        return base58.b58encode(self.private_key).decode('utf8'), base58.b58encode(self.nonce).decode('utf8')

    def encrypt_file(self, src_full_path: Path) -> Path:
        dst_full_path = Path(src_full_path.as_posix() + '.encryption')
        with open(src_full_path.as_posix(), 'rb') as f:
            data = f.read()
        cipher_msg = self.box.encrypt(data, self.nonce)
        with open(dst_full_path.as_posix(), 'wb') as f:
            f.write(cipher_msg.ciphertext)
        return dst_full_path

    def decrypt_file(self, src_full_path: Path):
        dst_full_path = Path(src_full_path.as_posix() + '.decryption')
        with open(src_full_path.as_posix(), 'rb') as f:
            data = f.read()
        plain_data = self.box.decrypt(data, self.nonce)
        with open(dst_full_path.as_posix(), 'wb') as f:
            f.write(plain_data)
        return dst_full_path

    @staticmethod
    def __get_cipher(is_server: bool, other_side_public_key: str = None):
        auth_ = auth.Auth()
        doc = auth_.doc
        cipher = doc.create_curve25519_cipher(auth_.did_str, 3, hive_setting.PASSWORD, is_server)
        if other_side_public_key is not None:
            cipher.set_other_side_public_key(base58.b58decode(bytes(other_side_public_key, 'utf8')))
        return cipher

    @staticmethod
    def get_service_did_public_key(is_server: bool):
        public_key = Encryption.__get_cipher(is_server).get_curve25519_public_key()
        return base58.b58encode(bytes(public_key)).decode('utf8')

    @staticmethod
    def encrypt_file_with_curve25519(src_full_path: Path, other_side_public_key: str, is_server: bool) -> Path:
        dst_full_path = Path(src_full_path.as_posix() + '.encryption.curve25519')
        stream = Encryption.__get_cipher(is_server, other_side_public_key).create_encryption_stream()
        total_size = src_full_path.stat().st_size
        remain = total_size

        with open(src_full_path, 'rb') as sf:
            with open(dst_full_path, 'wb') as df:  # header + encrypted data
                df.write(bytes(stream.header()))
                while remain > 0:
                    data = sf.read(min(remain, Encryption.TRUNK_SIZE))
                    if not data:
                        break

                    cipher_data = stream.push(data, remain - len(data) <= 0)
                    df.write(bytes(cipher_data))

                    remain -= len(data)

        return dst_full_path

    @staticmethod
    def decrypt_file_with_curve25519(src_full_path: Path, other_side_public_key: str, is_server: bool) -> Path:
        dst_full_path = Path(src_full_path.as_posix() + '.decryption.curve25519')
        total_size = src_full_path.stat().st_size
        remain = total_size

        if remain <= CipherDecryptionStream.header_len():
            raise BadRequestException('Too short data for curve25519 decryption.')

        with open(src_full_path, 'rb') as sf:
            header = sf.read(CipherDecryptionStream.header_len())
            stream = Encryption.__get_cipher(is_server, other_side_public_key).create_decryption_stream(header)

            with open(dst_full_path, 'wb') as df:
                while remain > 0:
                    data = sf.read(min(remain, Encryption.TRUNK_SIZE + CipherDecryptionStream.extra_encryption_size()))
                    if not data:
                        break

                    plain_data = stream.pull(data)
                    df.write(bytes(plain_data))

                    remain -= len(data)

        return dst_full_path
