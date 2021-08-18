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
    files.reading_operation, files.writing_operation, files.move_file, files.delete_file,
    scripting.register_script, scripting.call_script, scripting.call_script_url, scripting.delete_script,
    scripting.upload_file, scripting.download_file,
    backup.get_state, backup.backup_restore

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
  :endpoints: files.reading_operation

copy/upload
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: files.writing_operation

move
----

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: files.move_file

delete
------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: files.delete_file

05 Scripting
============

The scripting module supports share the data of the vault service for other users.

register script
---------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting.register_script

call script
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting.call_script

call script url
---------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting.call_script_url

unregister script
-----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting.delete_script

upload file
-----------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting.upload_file

download file
-------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: scripting.download_file

06 Backup
============

The backup module is for backup data to other hive node.
The credential is required for the vault service to access the backup service.

get state
---------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: backup.get_state

backup & restore
----------------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: backup.backup_restore
