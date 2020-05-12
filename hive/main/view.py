from flask import Blueprint, request, jsonify
from hive.main.hive_mongo import HiveMongo

hive = HiveMongo()
main = Blueprint('main', __name__)


def init_app(app):
    hive.init_app(app)
    app.register_blueprint(main)


@main.route('/api/v1/echo', methods=['POST'])
def echo():
    # get_json(force=False, silent=False, cache=True)
    # 获取json失败会直接返回
    content = request.get_json()
    return jsonify(content)


@main.route('/api/v1/did/register', methods=['POST'])
def did_register_view():
    return hive.did_register()


@main.route('/api/v1/did/login', methods=['POST'])
def did_login_view():
    return hive.did_login()


@main.route('/api/v1/db/create_collection', methods=['POST'])
def create_collection_view():
    return hive.create_collection()
