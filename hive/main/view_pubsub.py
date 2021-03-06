from flask import Blueprint
from hive.main.hive_pubsub import HivePubSub

h_pubsub = HivePubSub()
hive_pubsub = Blueprint('hive_pubsub', __name__)


def init_app(app, mode):
    h_pubsub.init_app(app)
    app.register_blueprint(hive_pubsub)


@hive_pubsub.route('/api/v1/pubsub/publish', methods=['POST'])
def pb_publish_channel():
    return h_pubsub.publish_channel()


@hive_pubsub.route('/api/v1/pubsub/channels', methods=['GET'])
def pb_get_channels():
    return h_pubsub.get_channels()


@hive_pubsub.route('/api/v1/pubsub/subscribe', methods=['POST'])
def pb_subscribe_channel():
    return h_pubsub.subscribe_channel()


@hive_pubsub.route('/api/v1/pubsub/push', methods=['POST'])
def pb_push_message():
    return h_pubsub.push_message()


@hive_pubsub.route('/api/v1/pubsub/pop', methods=['POST'])
def pb_pop_messages():
    return h_pubsub.pop_messages()
