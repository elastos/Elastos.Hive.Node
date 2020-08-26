from flask import Blueprint, request, jsonify

from hive.main.hive_mongo import HiveMongoDb

h_mongo_db = HiveMongoDb()

hive_db = Blueprint('hive_db', __name__)


def init_app(app):
    h_mongo_db.init_app(app)
    app.register_blueprint(hive_db)


@hive_db.route('/api/v1/db/create_collection', methods=['POST'])
def view_create_collection():
    return h_mongo_db.create_collection()


@hive_db.route('/api/v1/db/delete_collection', methods=['POST'])
def view_delete_collection():
    return h_mongo_db.delete_collection()


@hive_db.route('/api/v1/db/insert_one', methods=['POST'])
def view_insert_one():
    return h_mongo_db.insert_one()


@hive_db.route('/api/v1/db/insert_many', methods=['POST'])
def view_insert_many():
    return h_mongo_db.insert_many()


@hive_db.route('/api/v1/db/update_one', methods=['POST'])
def view_update_one():
    return h_mongo_db.update_one()


@hive_db.route('/api/v1/db/update_many', methods=['POST'])
def view_update_many():
    return h_mongo_db.update_many()


@hive_db.route('/api/v1/db/delete_one', methods=['POST'])
def view_delete_one():
    return h_mongo_db.delete_one()


@hive_db.route('/api/v1/db/delete_many', methods=['POST'])
def view_delete_many():
    return h_mongo_db.delete_many()


@hive_db.route('/api/v1/db/count_documents', methods=['POST'])
def view_count_documents():
    return h_mongo_db.count_documents()


@hive_db.route('/api/v1/db/find_one', methods=['POST'])
def view_find_one():
    return h_mongo_db.find_one()


@hive_db.route('/api/v1/db/find_many', methods=['POST'])
def view_find_many():
    return h_mongo_db.find_many()
