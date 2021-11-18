# -*- coding: utf-8 -*-

"""
The view of the hive-node and vault management.
"""
from flask import Blueprint

from src.modules.management.node_management import NodeManagement
from src.modules.management.vault_management import VaultManagement

blueprint = Blueprint('management', __name__)
node_management: NodeManagement = None
vault_management: VaultManagement = None


def init_app(app):
    """ This will be called by application initializer. """
    global node_management, vault_management
    node_management, vault_management = NodeManagement(), VaultManagement()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/management/node/vaults', methods=['GET'])
def get_vaults():
    """ Get all vault information in this hive node.

    .. :quickref: 09 Management; Get Vaults

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "vaults": [{
                "id": ObjectId,
                "pricing_using": <pricing name|str>,
                "max_storage": <int>,
                "file_use_storage": <int>,
                "cache_use_storage": <int>,
                "db_use_storage": <int>,
                "owner_did": <user did|str>,
            }]
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return node_management.get_vaults()


@blueprint.route('/api/v2/management/node/backups', methods=['GET'])
def get_backups():
    """ Get all backup information in this hive node.

    .. :quickref: 09 Management; Get Backups

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "backups": [{
                "pricing_using": <pricing name|str>,
                "max_storage": <int>,
                "use_storage": <int>,
                "owner_did": <user did|str>,
            }]
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return node_management.get_backups()


@blueprint.route('/api/v2/management/node/users', methods=['GET'])
def get_users():
    """ Get all user information in this hive node.

    .. :quickref: 09 Management; Get Users

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "users": [{
                "did": <user did|str>,
                "last_access": <timestamp|int>,
            }]
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return node_management.get_users()


@blueprint.route('/api/v2/management/node/payments', methods=['GET'])
def get_payments():
    """ Get all payment information in this hive node.

    .. :quickref: 09 Management; Get Payments

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "payments": [{
                "order_id": <str>,
                "receipt_id": <str>,
                "user_did": <str>,
                "subscription": <vault,backup|str>,
                "pricing_name": <str>,
                "ela_amount": <float>,
                "ela_address": <str>,
                "paid_did": <user did|str>,
            }]
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return node_management.get_payments()


@blueprint.route('/api/v2/management/node/vaults', methods=['DELETE'])
def delete_vaults():
    """ Delete the vaults by id in this hive node.

    .. :quickref: 09 Management; Delete Vaults

    **Request**:

    .. code-block:: json

        {
            "ids": [<str>, ]
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 No Content

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return node_management.delete_vaults()


@blueprint.route('/api/v2/management/node/vaults', methods=['DELETE'])
def delete_backups():
    """ Get backups by id in this hive node.

    .. :quickref: 09 Management; Delete Backups

    **Request**:

    .. sourcecode:: http

        {
            "ids": [<str>, ]
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 No Content

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return node_management.delete_backups()


@blueprint.route('/api/v2/management/node/apps', methods=['GET'])
def get_apps():
    """ Get all application information in the user vault.

    .. :quickref: 09 Management; Get Applications

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "apps": [{
                "user_did": <str>,
                "app_did": <str>,
                "database_name": <str>,
                "file_use_storage": <int>,
                "db_use_storage": <int>,
            }]
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return vault_management.get_apps()


@blueprint.route('/api/v2/management/node/apps', methods=['DELETE'])
def delete_apps():
    """ Delete the data of the application in the user vault.

    .. :quickref: 09 Management; Delete Application

    **Request**:

    .. sourcecode:: http

        {
            "app_dids": [<str>, ]
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 No Content

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """

    return vault_management.delete_apps()
