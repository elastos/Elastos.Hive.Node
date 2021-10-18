# -*- coding: utf-8 -*-

"""
The view of scripting module.
"""
from flask import Blueprint
import json

from src.modules.scripting.scripting import Scripting

blueprint = Blueprint('scripting-deprecated', __name__)
scripting: Scripting = None


def init_app(app):
    """ This will be called by application initializer. """
    global scripting
    scripting = Scripting()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/scripting-deprecated/<script_name>', methods=['PATCH'])
def call_script(script_name):
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
    return scripting.run_script(script_name)


@blueprint.route('/api/v2/vault/scripting-deprecated/<script_name>/<context_str>/<params>', methods=['GET'])
def call_script_url(script_name, context_str, params):
    """ Run the script registered by the owner by the URL parameters.

    This is the same as **Run Script**.

    .. :quickref: 05 Scripting; Run Script URL

    **URL Parameters**:

    .. sourcecode:: http

        <context_str> # context for running the script.
        <params> # params for running the script.

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
    return scripting.run_script_url(script_name, target_did, target_app_did, json.loads(params))


@blueprint.route('/api/v2/vault/scripting-deprecated/stream/<transaction_id>', methods=['PUT'])
def upload_file(transaction_id):
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
    return scripting.upload_file(transaction_id)


@blueprint.route('/api/v2/vault/scripting-deprecated/stream/<transaction_id>', methods=['GET'])
def download_file(transaction_id):
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
    return scripting.download_file(transaction_id)
