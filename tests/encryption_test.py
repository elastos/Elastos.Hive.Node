# -*- coding: utf-8 -*-

"""
Testing file for the about module.
"""
import unittest

import base58
import nacl.secret
import nacl.utils

from src.modules.backup.encryption import Encryption
from src.modules.files.local_file import LocalFile
from src.utils.did.did_wrapper import DIDDocument, Cipher, CipherDecryptionStream, CipherEncryptionStream
from src.settings import hive_setting
from tests.utils.http_client import HttpClient
from tests import init_test


class CipherTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.identifier = 'hive.node.test.cipher.identifier'
        self.security_code = 3
        self.user_did_doc: DIDDocument = HttpClient(f'/api/v2').remote_resolver.user_did.doc
        self.user_did_doc2: DIDDocument = HttpClient(f'/api/v2').remote_resolver.user_did2.doc

    @unittest.skip
    def test_encryption(self):
        def assert_buffer_equal(buf1, buf2):
            self.assertEqual(len(buf1), len(buf2))
            for i in range(len(buf1)):
                self.assertEqual(buf1[i], buf2[i:i+1])

        def check_ciphers(c1: Cipher, c2: Cipher):
            data1, data2, data3 = b'data1', b'data2', b'data3'
            nonce = bytearray.fromhex('404142434445464748494a4b4c4d4e4f5051525354555657')

            cipher_text = c1.encrypt(data1, nonce)
            clear_text = c2.decrypt(cipher_text, nonce)
            assert_buffer_equal(clear_text, data1)

            encryption_stream: CipherEncryptionStream = c1.create_encryption_stream()
            decryption_stream: CipherDecryptionStream = c2.create_decryption_stream(encryption_stream.header())
            cipher_text1 = encryption_stream.push(data1, False)
            cipher_text2 = encryption_stream.push(data2, False)
            cipher_text3 = encryption_stream.push(data3, True)
            clear_text1 = decryption_stream.pull(cipher_text1)
            clear_text2 = decryption_stream.pull(cipher_text2)
            clear_text3 = decryption_stream.pull(cipher_text3)
            self.assertTrue(decryption_stream.is_complete())
            assert_buffer_equal(clear_text1, data1)
            assert_buffer_equal(clear_text2, data2)
            assert_buffer_equal(clear_text3, data3)

        cipher: Cipher = self.user_did_doc.create_cipher(self.identifier, self.security_code, hive_setting.PASSWORD)
        check_ciphers(cipher, cipher)

        cipher1: Cipher = self.user_did_doc.create_curve25519_cipher(self.identifier, self.security_code, hive_setting.PASSWORD, False)
        cipher2: Cipher = self.user_did_doc2.create_curve25519_cipher(self.identifier, self.security_code, hive_setting.PASSWORD, False)
        cipher1.set_other_side_public_key(cipher2.get_curve25519_public_key())
        cipher2.set_other_side_public_key(cipher1.get_curve25519_public_key())

        check_ciphers(cipher1, cipher2)
        check_ciphers(cipher2, cipher1)

    @unittest.skip
    def test_encryption2(self):
        message = b'hello world' * 1000
        tmp_file = LocalFile.generate_tmp_file_path()
        with open(tmp_file, 'wb') as f:
            f.write(message)

        pk_client = pk_server = Encryption.get_service_did_public_key(False)
        cipher_path = Encryption.encrypt_file_with_curve25519(tmp_file, pk_client, True)
        plain_path = Encryption.decrypt_file_with_curve25519(cipher_path, pk_server, False)

        with open(plain_path, 'rb') as f:
            plain_data = f.read()

        self.assertEqual(message, plain_data)

    @unittest.skip
    def test_pynacl(self):
        message = b"The president will be exiting through the lower levels"
        key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        box = nacl.secret.SecretBox(key)
        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)

        encrypted = box.encrypt(message, nonce)
        plaintext = box.decrypt(encrypted.ciphertext, nonce)
        self.assertEqual(plaintext, message)

    @unittest.skip
    def test_ffi_buffer(self):
        cipher1: Cipher = self.user_did_doc.create_curve25519_cipher(self.identifier, self.security_code, hive_setting.PASSWORD, False)
        data = bytes(cipher1.get_curve25519_public_key())
        # key bytes -> base58 bytes -> str
        encode_data = base58.b58encode(data).decode('utf8')
        # str -> base58 bytes -> key bytes
        decode_data = base58.b58decode(bytes(encode_data, 'utf8'))
        print(data, encode_data, decode_data)
        self.assertEqual(data, decode_data)
