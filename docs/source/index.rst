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
    database.update_document, database.delete_document, database.find_document, database.query_document

Auth
====

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: auth.did_sign_in, auth.did_auth

Database
========

.. autoflask:: src:make_port()
  :undoc-static:
  :endpoints: database.create_collection, database.delete_collection, database.insert_or_count_document,
    database.update_document, database.delete_document, database.find_document, database.query_document
