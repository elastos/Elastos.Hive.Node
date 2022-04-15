# -*- coding: utf-8 -*-
from src.utils.did.did_wrapper import ElaError
from src.utils.did.entity import Entity


class V1Entity(Entity):
    def __init__(self, name, mnemonic=None, passphrase=None, storepass=None, need_resolve=True, from_file=False, file_content=None):
        Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase, storepass=storepass,
                        need_resolve=need_resolve, from_file=from_file, file_content=file_content)
        self.storepass = storepass

    def get_did_store(self):
        return self.did_store.store

    def get_did(self):
        return self.did.did

    def get_document(self):
        return self.doc.doc

    def get_store_password(self):
        return self.storepass

    def get_error_message(self, prompt=None) -> str:
        return ElaError.get(prompt)
