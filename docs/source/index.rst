Hive Node API Documentation
===========================

Here is the documents for the APIs of the hive node. The hive node supports the following service:

- authentication and authorization
- the subscription of the vault service
- the services under the vault: database, files, scripting, payment, backup
- the subscription of the backup service

Summary
=======

.. qrefflask:: src:make_port(is_first=True)
  :undoc-static:
  :endpoints: auth.did_sign_in, auth.did_auth,
    subscription.vault_subscribe, subscription.vault_unsubscribe, subscription.vault_get_info,
    subscription.backup_subscribe, subscription.backup_unsubscribe, subscription.backup_get_info,
    subscription.vault_get_price_plan,
    database.create_collection, database.delete_collection, database.insert_or_count_document,
    database.update_document, database.delete_document, database.find_document, database.query_document,
    files-deprecated.reading_operation, files-deprecated.writing_operation, files-deprecated.move_file,
    files-deprecated.delete_file,
    scripting-deprecated.register_script, scripting-deprecated.call_script, scripting-deprecated.call_script_url,
    scripting-deprecated.delete_script, scripting-deprecated.upload_file, scripting-deprecated.download_file,
    backup-deprecated.get_state, backup-deprecated.backup_restore,
    payment.get_version, payment.place_order, payment.pay_order, payment.get_orders, payment.get_receipt_info,
    about.get_version, about.get_commit_id

01 Auth
=======

The authentication and authorization is for other hive node services.

For accessing the services of the node, signing in with the DID document of the application
and getting the access token is first step.

To use the token returned by auth API. Please add this key-value in the header.

.. sourcecode:: http

    Authorization: token <the token returned by auth API>

sign in
-------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: auth.did_sign_in

auth
----

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: auth.did_auth

02 Subscription
===============

subscription for the vault service and the backup service.

vault subscribe
---------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.vault_subscribe

vault unsubscribe
-----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.vault_unsubscribe

get vault info.
---------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.vault_get_info

backup subscribe
----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.backup_subscribe

backup unsubscribe
------------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.backup_unsubscribe

get backup info.
----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.backup_get_info

get pricing plans
-----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.vault_get_price_plan

03 Database
===========

based on mongodb.

create collection
-----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.create_collection

delete collection
-----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.delete_collection

insert or count documents
-------------------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.insert_or_count_document

update documents
----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.update_document

delete documents
----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.delete_document

find documents
--------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.find_document

query documents
---------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.query_document

04 Files
========

files storage and management.

download/properties/hash/list
-----------------------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: files-deprecated.reading_operation

copy/upload
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: files-deprecated.writing_operation

move
----

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: files-deprecated.move_file

delete
------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: files-deprecated.delete_file

05 Scripting
============

The scripting module supports share the data of the vault service for other users.

register script
---------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting-deprecated.register_script

call script
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting-deprecated.call_script

call script url
---------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting-deprecated.call_script_url

unregister script
-----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting-deprecated.delete_script

upload file
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting-deprecated.upload_file

download file
-------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting-deprecated.download_file

06 Backup
=========

The backup module is for backup data to other hive node.
The credential is required for the vault service to access the backup service.

get state
---------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: backup-deprecated.get_state

backup & restore
----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: backup-deprecated.backup_restore

07 Payment
==========

The payment module is for upgrading the vault or the backup service.

get version
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: payment.get_version

place order
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: payment.place_order

pay order
---------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: payment.pay_order

get orders
----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: payment.get_orders

get receipt
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: payment.get_receipt_info

08 About
========

Show some information of the hive node. No authentication is required.

get version
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: about.get_version

get commit id
-------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: about.get_commit_id

Appendix A: Collections
=======================

auth_register
-------------

This common collection is for sign-in and auth.

.. code-block:: json

    {
        "_id": ObjectId,
        "appInstanceDid": <str>,
        "userDid": <str>,
        "nonce": <for generate token: str>,
        "nonce_expired": <int>,
        "appDid": <str>,
        "token": <str>,
        "token_expired": <int>
    }

vault_service
-------------

This common collection keeps the information for the vault.

.. code-block:: json

    {
        "_id": ObjectId,
        "did": <user_did: str>,
        "max_storage": <int>,
        "file_use_storage": <int>,
        "db_use_storage": <int>,
        "start_time": <timestamp: float>,
        "end_time": <timestamp, -1 means no end time: float>,
        "modify_time": <timestamp: float>,
        "state": <vault status: str>,
        "pricing_using": <pricing name: str>
    }

vault_order
-----------

This common collection keeps the information for the payment order.

.. code-block:: json

    {
        "_id": ObjectId,
        "user_did": <str>,
        "subscription": <"vault", "backup": str>,
        "pricing_name": <pricing name: str>,
        "ela_amount": <float>,
        "ela_address": <str>,
        "proof": <str>,
        "status": <str>,
        "created": <timestamp: float>,
        "modified": <timestamp: float>
    }

vault_receipt
-------------

This common collection keeps the information for the payment receipt.

.. code-block:: json

    {
        "_id": ObjectId,
        "user_did": <str>,
        "order_id": <str>,
        "transaction_id": <str>,
        "paid_did": <str>,
        "proof": <str>,
        "status": <str>,
        "created": <timestamp: float>,
        "modified": <timestamp: float>
    }

ipfs_backup_client
------------------

This common collection keeps the backup information in the vault node.

.. code-block:: json

    {
        "_id": ObjectId,
        "user_did": <str>,
        "type": "hive_node",
        "action": <"backup", "restore": str>,
        "state": <str>,
        "state_msg": <str>,
        "target_host": <str>,
        "target_did": <str>,
        "target_token": <str>,
        "created": <timestamp: float>,
        "modified": <timestamp: float>
    }

ipfs_cid_ref
------------

This common collection keeps the IPFS CID reference count in the vault or backup node.

.. code-block:: json

    {
        "_id": ObjectId,
        "cid": <str>,
        "count": <int>,
        "created": <timestamp: float>,
        "modified": <timestamp: float>
    }

ipfs_backup_server
------------------

This common collection keeps the backup information in the backup node.

.. code-block:: json

    {
        "_id": ObjectId,
        "user_did": <str>,
        "backup_using": <pricing name: str>,
        "max_storage": <int>,
        "use_storage": <int>,
        "start_time": <timestamp: float>,
        "end_time": <timestamp, -1 means no end time: float>,
        "created": <timestamp: float>,
        "modified": <timestamp: float>,
        "req_action": <"backup", "restore": str>,
        "req_cid": <str>,
        "req_sha256": <str>,
        "req_size": <int>,
        "req_state": <str>,
        "req_state_msg": <str>
    }

ipfs_files
----------

This user collection keeps the metadata of the files.

.. code-block:: json

    {
        "_id": ObjectId,
        "user_did": <str>,
        "app_did": <str>,
        "path": <file relative path: str>,
        "sha256": <str>,
        "is_file": <bool>
        "size": <int>,
        "ipfs_cid": <int>,
        "created": <timestamp: float>,
        "modified": <timestamp: float>
    }

scripts
-------

This user collection keeps the scripts from scripting module.

.. code-block:: json

    {
        "_id": ObjectId,
        "name": <script name: str>,
        "executable": <executable definition: dict>,
        "condition": <condition definition: dict>,
        "allowAnonymousUser": <bool>,
        "allowAnonymousApp": <bool>
    }

scripts_temptx
--------------

This user collection keeps the transaction information for scripts.

.. code-block:: json

    {
        "_id": ObjectId,
        "document": {
            "file_name": <file relative path: str>,
            "fileapi_type": <"upload", "download": str>
        },
        "anonymous": <bool>,
        "created": <timestamp: float>,
        "modified": <timestamp: float>
    }
