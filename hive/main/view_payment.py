from flask import Blueprint

from hive.main.hive_payment import HivePayment

h_payment = HivePayment()
hive_payment = Blueprint('hive_payment', __name__)


def init_app(app):
    h_payment.init_app(app)
    app.register_blueprint(hive_payment)


@hive_payment.route('/api/v1/payment/vault_package_info', methods=['GET'])
def get_vault_package_info():
    return h_payment.get_vault_package_info()


@hive_payment.route('/api/v1/payment/free_trial', methods=['POST'])
def start_trial():
    return h_payment.start_trial()


@hive_payment.route('/api/v1/payment/create_vault_package_order', methods=['POST'])
def create_vault_package_order():
    return h_payment.create_vault_package_order()


@hive_payment.route('/api/v1/payment/pay_vault_package_order', methods=['POST'])
def pay_vault_package_order():
    return h_payment.pay_vault_package_order()


@hive_payment.route('/api/v1/payment/vault_package_order', methods=['GET'])
def vault_package_order():
    return h_payment.get_vault_package_order()


@hive_payment.route('/api/v1/payment/vault_package_order_list', methods=['GET'])
def vault_package_order_list():
    return h_payment.get_vault_package_order_list()


@hive_payment.route('/api/v1/service/vault', methods=['GET'])
def get_vault_service_info():
    return h_payment.get_vault_service_info()
