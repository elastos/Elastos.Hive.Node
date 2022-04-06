# -*- coding: utf-8 -*-

"""
The view of subscription module.
"""
from flask import Blueprint

from src.modules.deprecated.backup import BackupServer

blueprint = Blueprint('subscription-deprecated', __name__)
backup_server: BackupServer = None


def init_app(app):
    """ This will be called by application initializer. """
    global backup_server
    backup_server = BackupServer()
    app.register_blueprint(blueprint)


###############################################################################
# blow is for backup.


@blueprint.route('/api/v2/subscription-deprecated/backup', methods=['GET'])
def backup_get_info():
    """ Get the information of the owned backup service.

    The information contains something like storage usage, pricing plan, etc.

    .. :quickref: 02 Subscription; Get Backup Info.

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
             “service_did”: “did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN"”,
             “storage_quota: 500，
             “storage_used”: 20,
             “created”: 1602236316,   // epoch time.
             “updated”: 1604914928,
             “pricing_plan”: “rookie”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """
    return backup_server.get_info()


@blueprint.route('/api/v2/subscription-deprecated/backup', methods=['PUT'])
def backup_subscribe():
    """ Subscribe to a remote backup service on the specific hive node.
    With the backup service, the data of the vault service can backup for data security.

    .. :quickref: 02 Subscription; Backup Subscribe

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            “pricingPlan”: “<the using pricing plan>
            “serviceDid”: <hive node service did>
            “quota”: 50000000, # the max space of the storage for the vault service.
            “used”: 0,
            “created”: <the epoch time>
            “updated”: <the epoch time>
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 455 Already Exists

    """
    return backup_server.subscribe()


@blueprint.route('/api/v2/subscription/backup', methods=['POST'])
def backup_activate_deactivate():
    op = None
    if op == 'activation':
        return backup_server.activate()
    elif op == 'deactivation':
        return backup_server.deactivate()


@blueprint.route('/api/v2/subscription-deprecated/backup', methods=['DELETE'])
def backup_unsubscribe():
    """ Unsubscribe from the remote backup service on a specific hive node.

    The data on the backup node would be unsafe and undefined or even deleted from the hive node.

    .. :quickref: 02 Subscription; Backup Unsubscribe

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 No Content

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    """
    return backup_server.unsubscribe()
