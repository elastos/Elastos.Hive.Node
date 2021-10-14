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
