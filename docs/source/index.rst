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
    subscription.vault_subscribe,
    database.create_collection, database.delete_collection, database.insert_or_count_document,
    database.update_document, database.delete_document, database.find_document, database.query_document,
    files.reading_operation, files.writing_operation, files.move_file, files.delete_file

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

subscribe
---------

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: subscription.vault_subscribe

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
