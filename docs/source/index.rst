Hive Node API Documentation
===========================

Here is the documents for the APIs of the hive node. The hive node supports the following service:

- authentication and authorization
- the subscription of the vault service.
- the services under the vault: database, files, scripting, payment, backup
- the subscription of the backup service.

Summary
=======

.. qrefflask:: src:make_port(is_first=True)
  :undoc-static:
  :endpoints: auth.did_sign_in, auth.did_auth,
    database.create_collection, database.delete_collection, database.insert_or_count_document,
    database.update_document, database.delete_document, database.find_document, database.query_document,
    files.reading_operation, files.writing_operation, files.move_file, files.delete_file

Auth
====

authentication and authorization

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

Database
========

based on mongodb

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

Files
=====

Files storage and management.

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
