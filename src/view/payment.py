# -*- coding: utf-8 -*-

"""
The view of payment module.
"""
from flask import Blueprint, request

from src.modules.payment.payment import Payment

blueprint = Blueprint('payment', __name__)
payment: Payment = None


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global payment
    payment = Payment(app, hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/payment/version', methods=['GET'])
def get_version():
    return payment.get_version()


@blueprint.route('/api/v2/payment/order', methods=['PUT'])
def place_order():
    return payment.place_order(request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/payment/order/<order_id>', methods=['POST'])
def pay_order(order_id):
    return payment.pay_order(order_id, request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/payment/order', methods=['GET'])
def get_orders():
    subscription, order_id = request.args.get('subscription'), request.args.get('order_id')
    return payment.get_orders(subscription, order_id)


@blueprint.route('/api/v2/payment/receipt', methods=['GET'])
def get_receipt_info():
    return payment.get_receipt_info(request.args.get('order_id'))