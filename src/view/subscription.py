# -*- coding: utf-8 -*-

"""
The view of subscription module.
"""
from flask import Blueprint, request

from src.modules.backup.backup_server import BackupServer
from src.modules.subscription.subscription import VaultSubscription

blueprint = Blueprint('subscription', __name__)
vault_subscription: VaultSubscription = None
backup_server: BackupServer = BackupServer()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global vault_subscription, backup_server
    vault_subscription = VaultSubscription(app, hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/subscription/pricing_plan', methods=['GET'])
def vault_get_price_plan():
    subscription, name = request.args.get("subscription"), request.args.get("name")
    return vault_subscription.get_price_plans(subscription, name)


@blueprint.route('/api/v2/subscription/vault', methods=['GET'])
def vault_get_info():
    return vault_subscription.get_info()


@blueprint.route('/api/v2/subscription/vault', methods=['PUT'])
def vault_subscribe():
    """ Subscribe to a remote vault service on the specific hive node,
    where would create a new vault service if no such vault existed against the DID used.

    A user can subscribe to only one vault service on the specific hive node with a given DID,
    then should declare that service endpoint on the DID document that would be published on the DID chain
    so that other users could be aware of the address and access the data on that vault with certain permission.

    The free pricing plan is applied to a new subscribed vault.
    The payment APIs will be used for upgrading the vault service.

    .. :quickref: 02 Subscription; Subscribe

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 Created

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

    .. :quickref: 02 Subscription; Unsubscribe

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
    return backup_server.get_info()


@blueprint.route('/api/v2/subscription/backup', methods=['PUT'])
def backup_subscribe():
    credential = request.args.get('credential')
    return backup_server.subscribe(credential)


@blueprint.route('/api/v2/subscription/backup', methods=['POST'])
def backup_activate_deactivate():
    op = None
    if op == 'activation':
        return backup_server.activate()
    elif op == 'deactivation':
        return backup_server.deactivate()


@blueprint.route('/api/v2/subscription/backup', methods=['DELETE'])
def backup_unsubscribe():
    return backup_server.unsubscribe()
