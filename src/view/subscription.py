# -*- coding: utf-8 -*-

"""
The view of subscription module.
"""
from flask import Blueprint, request

from src.modules.subscription.subscription import VaultSubscription, BackupSubscription

blueprint = Blueprint('subscription', __name__)
vault_subscription = VaultSubscription()
backup_subscription = BackupSubscription()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    # global scripting
    # scripting = Scripting(app=app, hive_setting=hive_setting)
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
    credential = request.args.get('credential')
    return vault_subscription.subscribe(credential)


@blueprint.route('/api/v2/subscription/vault', methods=['POST'])
def vault_activate_deactivate():
    op = request.args.get('op')
    if op == 'activation':
        return vault_subscription.activate()
    elif op == 'deactivation':
        return vault_subscription.deactivate()


@blueprint.route('/api/v2/subscription/vault', methods=['DELETE'])
def vault_unsubscribe():
    return vault_subscription.unsubscribe()


@blueprint.route('/api/v2/subscription/backup', methods=['GET'])
def backup_get_info():
    return backup_subscription.get_info()


@blueprint.route('/api/v2/subscription/backup', methods=['PUT'])
def backup_subscribe():
    credential = request.args.get('credential')
    return backup_subscription.subscribe(credential)


@blueprint.route('/api/v2/subscription/backup', methods=['POST'])
def backup_activate_deactivate():
    op = None
    if op == 'activation':
        return backup_subscription.activate()
    elif op == 'deactivation':
        return backup_subscription.deactivate()


@blueprint.route('/api/v2/subscription/backup', methods=['DELETE'])
def backup_unsubscribe():
    return backup_subscription.unsubscribe()
