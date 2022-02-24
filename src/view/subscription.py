# -*- coding: utf-8 -*-

"""
The view of subscription module.
"""
from flask import Blueprint, request

from src.modules.backup.backup_server import BackupServer
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.modules.subscription.subscription import VaultSubscription

blueprint = Blueprint('subscription', __name__)
vault_subscription: VaultSubscription = None
backup_server: IpfsBackupServer = None


def init_app(app):
    """ This will be called by application initializer. """
    global vault_subscription, backup_server
    vault_subscription, backup_server = VaultSubscription(), IpfsBackupServer()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/subscription/pricing_plan', methods=['GET'])
def vault_get_price_plan():
    """ Get an available pricing plan list or the specific pricing plan for the vault and backup service.

    The pricing plan list is the pricing plans that the hive node supported for the vault service.
    The owner of the vault service can use the pricing plan name upgrade the vault service
    to get much more storage space.

    .. :quickref: 02 Subscription; Get Vault Pricing Plans.

    **URL Parameters**:

    .. sourcecode:: http

        subscription=all # possible value: all, vault or backup
        name=rookie # the pricing plan name

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "backupPlans": [{
                    amount": 0,
                        "currency": "ELA",
                    "maxStorage": 500,
                    "name": "Free",
                    "serviceDays": -1
                }, {
                    "amount": 1.5,
                    "currency": "ELA",
                    "maxStorage": 2000,
                    "name": "Rookie",
                     "serviceDays": 30
                }, {
                    "amount": 3,
                     "currency": "ELA",
                    "maxStorage": 5000,
                    "name": "Advanced",
                    "serviceDays": 30
                }],

            "pricingPlans": [{
                "amount": 0,
                "currency": "ELA",
                "maxStorage": 500,
                "name": "Free",
                "serviceDays": -1
            }, {
                "amount": 2.5,
                "currency": "ELA",
                "maxStorage": 2000,
                "name": "Rookie",
                "serviceDays": 30
            }, {
                 "amount": 5,
                "currency": "ELA",
                "maxStorage": 5000,
                "name": "Advanced",
                "serviceDays": 30
            }],
            "version": "1.0"
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """
    subscription, name = request.args.get("subscription"), request.args.get("name")
    return vault_subscription.get_price_plans(subscription, name)


@blueprint.route('/api/v2/subscription/vault', methods=['GET'])
def vault_get_info():
    """ Get the information of the owned vault service.

    The information contains something like storage usage, pricing plan, etc.

    .. :quickref: 02 Subscription; Get Vault Info.

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
    return vault_subscription.get_info()


@blueprint.route('/api/v2/subscription/vault/app_stats', methods=['GET'])
def vault_get_app_stats():
    """ Get all application stats in the user's vault.

    .. :quickref: 02 Subscription; Get App Stats

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

    return vault_subscription.get_app_stats()


@blueprint.route('/api/v2/subscription/vault', methods=['PUT'])
def vault_subscribe():
    """ Subscribe to a remote vault service on the specific hive node,
    where would create a new vault service if no such vault existed against the DID used.

    A user can subscribe to only one vault service on the specific hive node with a given DID,
    then should declare that service endpoint on the DID document that would be published on the DID chain
    so that other users could be aware of the address and access the data on that vault with certain permission.

    The free pricing plan is applied to a new subscribed vault.
    The payment APIs will be used for upgrading the vault service.

    .. :quickref: 02 Subscription; Vault Subscribe

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            “pricing_plan”: “<the using pricing plan>
            “service_did”: <hive node service did>
            “storage_quota”: 50000000, # the max space of the storage for the vault service.
            “storage_used”: 0,
            “created”: <the epoch time>
            “updated”: <the epoch time>
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 455 Already Exists

    """
    return vault_subscription.subscribe()


@blueprint.route('/api/v2/subscription/vault', methods=['POST'])
def vault_activate_deactivate():
    op = request.args.get('op')
    if op == 'activation':
        return vault_subscription.activate()
    elif op == 'deactivation':
        return vault_subscription.deactivate()


@blueprint.route('/api/v2/subscription/vault', methods=['DELETE'])
def vault_unsubscribe():
    """ Unsubscribe from the remote vault service on a specific hive node.
    Only the vault owner can unsubscribe from his owned vault service.
    After unsubscription, the vault service would stop rendering service,
    and users can not access data from the vault anymore.

    And the data on the vault would be unsafe and undefined or even deleted from the hive node.

    .. :quickref: 02 Subscription; Vault Unsubscribe

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
    return vault_subscription.unsubscribe()


###############################################################################
# blow is for backup.


@blueprint.route('/api/v2/subscription/backup', methods=['GET'])
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


@blueprint.route('/api/v2/subscription/backup', methods=['PUT'])
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
            “pricing_plan”: “<the using pricing plan>
            “service_did”: <hive node service did>
            “storage_quota”: 50000000, # the max space of the storage for the vault service.
            “storage_used”: 0,
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


@blueprint.route('/api/v2/subscription/backup', methods=['DELETE'])
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
