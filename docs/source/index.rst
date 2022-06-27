Hive Node API Documentation
===========================

Here is the documents for the APIs of the hive node. The hive node supports the following service:

- authentication and authorization
- the subscription of the vault service
- the services under the vault: database, files, scripting, payment, backup
- the subscription of the backup service

Summary
=======

.. qrefflask:: src:get_docs_app(first=True)
  :undoc-static:
  :endpoints: v2_auth.sign_in, v2_auth.auth,
    subscription.vault_subscribe, subscription.vault_unsubscribe, subscription.vault_info, subscription.vault_app_states,
    subscription.vault_activate_deactivate,
    subscription.backup_subscribe, subscription.backup_unsubscribe, subscription.backup_info, subscription.vault_price_plan,
    database.create_collection, database.delete_collection, database.insert_or_count,
    database.update, database.delete, database.find, database.query,
    files.reading_operation, files.writing_operation, files.move_file, files.delete_file,
    scripting.register_script, scripting.call_script, scripting.call_script_url,
    scripting.delete_script, scripting.upload_file, scripting.download_file,
    backup.state, backup.backup_restore, backup.server_promotion,
    payment.version, payment.place_order, payment.settle_order, payment.orders, payment.receipts,
    node.version, node.commit_id, node.info,
    provider.vaults, provider.backups, provider.filled_orders

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

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: v2_auth.sign_in

auth
----

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: v2_auth.auth

02 Subscription
===============

subscription for the vault service and the backup service.

vault subscribe
---------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.vault_subscribe

vault unsubscribe
-----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.vault_unsubscribe

get vault info.
---------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.vault_info

get app stats
-------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.vault_app_states

activate & deactivate
---------------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.vault_activate_deactivate

backup subscribe
----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.backup_subscribe

backup unsubscribe
------------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.backup_unsubscribe

get backup info.
----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.backup_info

get pricing plans
-----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: subscription.vault_price_plan

03 Database
===========

based on mongodb.

create collection
-----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: database.create_collection

delete collection
-----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: database.delete_collection

insert or count documents
-------------------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: database.insert_or_count

update documents
----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: database.update

delete documents
----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: database.delete

find documents
--------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: database.find

query documents
---------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: database.query

04 Files
========

files storage and management.

download/properties/hash/list
-----------------------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: files.reading_operation

copy/upload
-----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: files.writing_operation

move
----

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: files.move_file

delete
------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: files.delete_file

05 Scripting
============

The scripting module supports share the data of the vault service for other users.

register script
---------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: scripting.register_script

call script
-----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: scripting.call_script

call script url
---------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: scripting.call_script_url

unregister script
-----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: scripting.delete_script

upload file
-----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: scripting.upload_file

download file
-------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: scripting.download_file

06 Backup
=========

The backup module is for backup data to other hive node.
The credential is required for the vault service to access the backup service.

get state
---------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: backup.state

backup & restore
----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: backup.backup_restore

promote
----------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: backup.server_promotion

07 Payment
==========

The payment module is for upgrading the vault or the backup service.

get version
-----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: payment.version

place order
-----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: payment.place_order

settle order
------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: payment.settle_order

get orders
----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: payment.orders

get receipts
------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: payment.receipts

08 About
========

Show some information of the hive node. No authentication is required.

get version
-----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: node.version

get commit id
-------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: node.commit_id

get node information
--------------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: node.info

09 Provider
===========

The management for the hive node owner or the vault owner.

get vaults
----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: provider.vaults

get backups
-----------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: provider.backups

get payments
------------

.. autoflask:: src:get_docs_app()
  :undoc-static:
  :endpoints: provider.filled_orders

Appendix A: Error Response
==========================

When failed with API calling as some error happened in the hive node,
the error response will return, such as **HTTP/1.1 400 Bad Request**.

The body of the error response should contain the following format content
which will help caller debug the errors.

.. sourcecode:: http

    {
        “error”: {
            “message”: “the specific error description”, // [mandatory]
            “internal_code”:  <number> // [optional],
            ... //other customized items if it's necessary to report more information. [optional]
        }
    }

Appendix B: Collections
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

application
-----------

The applications belong to user DID

.. code-block:: json

    {
        "_id": ObjectId,
        "user_did": <str>,
        "app_did": <str>,
        "database_name": <str>,
        "state": "normal",
        "created": <timestamp: int, seconds>,
        "modified": <timestamp: int, seconds>
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
