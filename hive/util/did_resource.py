import json
import uuid

from pymongo import MongoClient

from hive.util.constants import DID_INFO_DB_NAME, DID_RESOURCE_COL, DID_RESOURCE_NAME, DID_RESOURCE_SCHEMA, \
    DID_RESOURCE_DID


# settings must be json string
def add_did_resource_to_db(did, resource, schema):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]

    did_dic = {DID_RESOURCE_DID: did, DID_RESOURCE_NAME: resource, DID_RESOURCE_SCHEMA: schema}
    i = col.insert_one(did_dic)
    return i


def update_schema_of_did_resource(did, resource, schema):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]

    query = {DID_RESOURCE_DID: did, DID_RESOURCE_NAME: resource}
    values = {"$set": {DID_RESOURCE_SCHEMA, schema}}
    r = col.update_one(query, values)
    return r


def find_schema_of_did_resource(did, resource):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]
    query = {DID_RESOURCE_DID: did, DID_RESOURCE_NAME: resource}
    data = col.find_one(query)
    if data is None:
        return None
    else:
        return data[DID_RESOURCE_SCHEMA]


def get_all_resource_of_did(did):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]
    query = {DID_RESOURCE_DID: did}
    resource_list = col.find(query)
    return resource_list


def delete_did_resource_from_db(did, resource):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]
    query = {DID_RESOURCE_DID: did, DID_RESOURCE_NAME: resource}
    data = col.delete_one(query)
    return data
