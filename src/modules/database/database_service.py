# -*- coding: utf-8 -*-

"""
The entrance for database module.
"""
import json
from bson import json_util

from flask import g

from src.utils.http_exception import InvalidParameterException, CollectionNotFoundException
from src.utils.http_request import RequestData
from src.modules.database.mongodb_client import MongodbClient
from src.modules.subscription.vault import VaultManager
from src.modules.database.collection_metadata import CollectionMetadata


class DatabaseService:
    """ Database service is for data saving and retrieving which is based on mongodb. """

    def __init__(self):
        self.mcli = MongodbClient()
        self.vault_manager = VaultManager()
        self.collection_metadata = CollectionMetadata()

    def create_collection(self, collection_name, is_encrypt, encrypt_method):
        """ Create collection by name

        :param collection_name: The collection name.
        :param is_encrypt: If the document of the collection has been encrypted.
        :param encrypt_method: The encrypt method when is_encrypt is True.
        :return: The collection name.
        """

        if self.mcli.is_internal_user_collection(collection_name):
            raise InvalidParameterException(f'No permission to create the collection {collection_name}')

        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        self.mcli.create_user_collection(g.usr_did, g.app_did, collection_name)
        self.collection_metadata.add(g.usr_did, g.app_did, collection_name, is_encrypt, encrypt_method)
        return {'name': collection_name}

    def delete_collection(self, collection_name):
        """ Delete collection by name

        :param collection_name: The collection name.
        :return: None
        """
        if self.mcli.is_internal_user_collection(collection_name):
            raise InvalidParameterException(f'No permission to delete the collection {collection_name}')

        self.vault_manager.get_vault(g.usr_did).check_write_permission()
        self.collection_metadata.delete(g.usr_did, g.app_did, collection_name)
        self.mcli.delete_user_collection(g.usr_did, g.app_did, collection_name, check_exist=True)

    def get_collections(self):
        """ Get all collection belonged to the user.

        :return: The list which contains every collection details.
        """

        self.vault_manager.get_vault(g.usr_did)

        self.collection_metadata.sync_all(g.usr_did, g.app_did)
        docs = self.collection_metadata.get_all(g.usr_did, g.app_did)
        if not docs:
            raise CollectionNotFoundException()

        return {
            'collections': list(map(lambda d: {
                'name': d['name'],
                'is_encrypt': d['is_encrypt'],
                'encrypt_method': d['encrypt_method']
            }, docs))
        }

    def insert_documents(self, collection_name, documents, options):
        """ Insert documents from the collection

        :param collection_name: The collection name.
        :param documents: The documents to be inserted.
        :param options: The options used to insert.
        :return: The insert result.
        """

        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        col = self.__get_collection(collection_name)
        return col.insert_many(documents, contains_extra=self.__is_timestamp(options), **options)

    def update_documents(self, collection_name, filter_, update, options, only_one):
        """ Update the documents of the collection

        :param collection_name: The collection name.
        :param filter_: The filter to get matched documents.
        :param update: The content for updating the matching documents.
        :param options: The options to update.
        :param only_one: Whether update only one matched document or all matched ones.
        :return: The update result.
        """

        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        col = self.__get_collection(collection_name)
        return col.update_many(filter_, update, contains_extra=self.__is_timestamp(options), only_one=only_one, **options)

    def delete_document(self, collection_name, filter_, only_one):
        """ Delete the documents of the collection

        :param collection_name: The collection name.
        :param filter_: The filter to get matched documents.
        :param only_one: Whether delete only one matched document or all matched ones.
        :return: None
        """

        self.vault_manager.get_vault(g.usr_did).check_write_permission()

        col = self.__get_collection(collection_name)
        col.delete_many(filter_, only_one=only_one)

    def count_document(self, collection_name, filter_, options):
        """ Count the documents of the collection

        :param collection_name: The collection name.
        :param filter_: The filter to get matched documents.
        :param options: The options to count.
        :return: The amount of matched documents.
        """

        self.vault_manager.get_vault(g.usr_did)

        col = self.__get_collection(collection_name)
        return {"count": col.count(filter_, **options)}

    def find_document(self, collection_name, filter_, skip, limit):
        """ Find the documents of the collection

        :param collection_name: The collection name.
        :param filter_: The filter to get matched documents.
        :param skip: Skip first n matched documents.
        :param limit: Limit the result size.
        :return: The matched documents list.
        """

        self.vault_manager.get_vault(g.usr_did)

        # options is optional
        options = {}
        if skip is not None:
            options['skip'] = skip
        if limit is not None:
            options['limit'] = limit

        return self.__do_internal_find(collection_name, filter_, options)

    def query_document(self, collection_name, filter_, options):
        """ Query the documents of the collection.
        Query API provides more options than Find.

        :param collection_name: The collection name.
        :param filter_: The filter to get matched documents.
        :param options: The options to query.
        :return: The matched documents list.
        """

        self.vault_manager.get_vault(g.usr_did)

        return self.__do_internal_find(collection_name, filter_, options)

    @staticmethod
    def __is_timestamp(options):
        RequestData(options, optional=True).validate_opt('timestamp', bool)
        return options.pop('timestamp', True)

    def __get_collection(self, collection_name):
        if self.mcli.is_internal_user_collection(collection_name):
            raise InvalidParameterException(f'No permission to operate the collection {collection_name}')

        return self.mcli.get_user_collection(g.usr_did, g.app_did, collection_name)

    def __do_internal_find(self, collection_name, filter_, options):
        col = self.__get_collection(collection_name)
        docs = col.find_many(filter_, **options)
        metadata = self.collection_metadata.get(g.usr_did, g.app_did, collection_name)
        return {
            'items': [c for c in json.loads(json_util.dumps(docs))],
            'is_encrypt': metadata['is_encrypt'] if metadata else False,
            'encrypt_method': metadata['encrypt_method'] if metadata else '',
        }
