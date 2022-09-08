# -*- coding: utf-8 -*-

"""
Testing file for the about module.
"""
import unittest

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

    # @unittest.skip
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

        pk1 = bytearray.fromhex('60257db4c5f26c9c5fa2f1f46b812abf01515af38d5e9d1cd5ed6f1507b6c661')
        pk2 = bytearray.fromhex('e4938b32ccaeb3c869a5f9e67425205b05d4a66583a5638fe37242aaeff7992f')
        cipher1: Cipher = self.user_did_doc.create_curve25519_cipher(self.identifier, self.security_code, hive_setting.PASSWORD, False, pk2)
        cipher2: Cipher = self.user_did_doc2.create_curve25519_cipher(self.identifier, self.security_code, hive_setting.PASSWORD, False, pk1)
        check_ciphers(cipher1, cipher2)

        # encrypt and decrypt on the same side.
        check_ciphers(cipher1, cipher1)
        check_ciphers(cipher2, cipher2)
