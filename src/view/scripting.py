# -*- coding: utf-8 -*-

"""
The view of ipfs module for files and scripting.
"""
import json

from flask_restful import Resource

from src.modules.scripting.scripting import Scripting
from src.utils.http_response import response_stream


class RegisterScript(Resource):
    def __init__(self):
        self.scripting = Scripting(is_ipfs=True)

    def put(self, script_name):
        """ Register a new script for the vault data owner by the script name.

        Script caller will run the script by name later.
        The script is treated as the channel for other users to access the owner's data.
        This will set up a condition and an executable.
        The condition is checked and must matches before running the executable.
        What the executable can do depends on the type of it.
        For example, the type "find" can query the documents from a collection.

        .. :quickref: 05 Scripting; Register

        **Request**:

        .. code-block:: json

            {
                "condition": {
                    "type": "queryHasResult",
                    "name": "verify_user_permission",
                    "body": {
                        "collection": "groups",
                        "filter": {
                            "_id": "$params.group_id",
                            "friends": "$caller_did"
                        }
                    }
                },
                "executable": {
                    "type": "find",
                    "name": "find_messages",
                    "output": true,
                    "body": {
                        "collection": "messages",
                        "filter": {
                            "group_id": "$params.group_id"
                        },
                        "options": {
                            "projection": {
                                "_id": false
                            },
                            "limit": 100
                        }
                    }
                },
                "allowAnonymousUser": false,
                "allowAnonymousApp": false
            }

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "find_messages": {
                    "acknowledged":true,
                    "matched_count":1,
                    "modified_count":1,
                    "upserted_id":null
                }
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        **Condition**

        There are three types of conditions: 'and', 'or', 'queryHasResult'. The 'and' and the 'or' are for merging
        other type conditions and can be recursive. 'queryHasResult' is for checking
        whether the document can be found in the collection by a filter. Here is an example for three types:

        .. code-block:: json

            {
               "condition":{
                  "type":"and",
                  "name":"verify_user_permission",
                  "body":[
                     {
                        "type":"or",
                        "name":"verify_user_permission",
                        "body":[
                           {
                              "type":"queryHasResult",
                              "name":"user_in_group",
                              "body":{
                                 "collection":"groups",
                                 "filter":{
                                    "_id":"$params.group_id",
                                    "friends":"$caller_did"
                                 }
                              }
                           },
                           {
                              "type":"queryHasResult",
                              "name":"user_in_group",
                              "body":{
                                 "collection":"groups",
                                 "filter":{
                                    "_id":"$params.group_id",
                                    "friends":"$caller_did"
                                 }
                              }
                           }
                        ]
                     },
                     {
                        "type":"queryHasResult",
                        "name":"user_in_group",
                        "body":{
                           "collection":"groups",
                           "filter":{
                              "_id":"$params.group_id",
                              "friends":"$caller_did"
                           }
                        }
                     }
                  ]
               }
            }


        **Executable**

        There are nine types of executables. Here lists all types with the relating examples.
        For the request params and the response, please check Run Script for how to use them.
        No response will be provided if the output option sets to false.

        Possible executable types are here:

        - aggregated
        - find
        - insert
        - update
        - delete
        - fileUpload
        - fileDownload
        - fileProperties
        - fileHash

        """
        return self.scripting.set_script(script_name)


class DeleteScript(Resource):
    def __init__(self):
        self.scripting = Scripting(is_ipfs=True)

    def delete(self, script_name):
        """ Remove the script by the script name and the script can not be called anymore.

        .. :quickref: 05 Scripting; Unregister

        **Request**:

        .. code-block:: json

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 204 No Content

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        return self.scripting.delete_script(script_name)


class CallScript(Resource):
    def __init__(self):
        self.scripting = Scripting(is_ipfs=True)

    def patch(self, script_name):
        """ Run the script registered by the owner.

        Before running the script, the caller needs to check if matches the script condition.
        The parameter 'context' is also required for tell the scripting service
        which did and app_did is the data belongs to.

        The 'params' parameter is used to provide the value which the script requires if exists.

        .. :quickref: 05 Scripting; Run Script

        **Request**:

        .. code-block:: json

            {
                "context": {
                    "target_did": "did:elastos:icXtpDnZRSDrjmD5NQt6TYSphFRqoo2q6n",
                    "target_app_did":"appId"
                },
                "params": {
                    "group_id": {"$oid": "5f8d9dfe2f4c8b7a6f8ec0f1"}
                }
            }

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
               "get_groups":{
                  "items":[
                     {
                        "name":"Tuum Tech"
                     }
                  ]
               }
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        return self.scripting.run_script(script_name)


class CallScriptUrl(Resource):
    def __init__(self):
        self.scripting = Scripting(is_ipfs=True)

    def get(self, script_name, context_str, params):
        """ Run the script registered by the owner by the URL parameters.

        This is the same as **Run Script**.

        .. :quickref: 05 Scripting; Run Script URL

        **URL Parameters**:

        .. sourcecode:: http

            <context_str> # context for running the script. format: <target_did>@<target_app_did>
            <params> # params for running the script with json format.

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
               "get_groups":{
                  "items":[
                     {
                        "name":"Tuum Tech"
                     }
                  ]
               }
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        target_did, target_app_did = None, None
        parts = context_str.split('@')
        if len(parts) == 2 and parts[0] and parts[1]:
            target_did, target_app_did = parts[0], parts[1]
        return self.scripting.run_script_url(script_name, target_did, target_app_did, json.loads(params))


class UploadFile(Resource):
    def __init__(self):
        self.scripting = Scripting(is_ipfs=True)

    def put(self, transaction_id):
        """ Upload file by transaction id returned by the running script for the executable type 'fileUpload'.

        .. :quickref: 05 Scripting; Upload File

        **Request**:

        .. sourcecode:: http

            <The bytes content of the file>

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        return self.scripting.upload_file(transaction_id)


class DownloadFile(Resource):
    def __init__(self):
        self.scripting = Scripting(is_ipfs=True)

    @response_stream
    def get(self, transaction_id):
        """ Download file by transaction id which is returned by running script for the executable type 'fileDownload'.

        .. :quickref: 05 Scripting; Download File

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            <The bytes content of the file>

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        return self.scripting.download_file(transaction_id)
