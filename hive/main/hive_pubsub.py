from datetime import datetime

from hive.main.interceptor import post_json_param_pre_proc, pre_proc
from hive.util.constants import PUB_CHANNEL_NAME
from hive.util.error_code import ALREADY_EXIST, NOT_FOUND
from hive.util.pubsub.pb_exchanger import pubsub_push_message
from hive.util.pubsub.publisher import pub_setup_channel, pub_add_subscriber, pub_remove_channel, \
    pub_remove_subscribe, pub_get_pub_channels, pub_get_sub_channels, pub_get_channel
from hive.util.pubsub.subscriber import sub_setup_message_subscriber, sub_pop_messages, sub_get_message_subscriber
from hive.util.server_response import ServerResponse


class HivePubSub:
    def __init__(self):
        self.app = None
        self.response = ServerResponse("HivePubSub")

    def init_app(self, app):
        self.app = app

    def publish_channel(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "channel_name")
        if err:
            return err
        channel_name = content["channel_name"]
        channel_id = pub_setup_channel(did, app_id, channel_name)
        if channel_id:
            return self.response.response_ok()
        else:
            return self.response.response_err(ALREADY_EXIST, f"Channel {channel_name} has exist")

    def remove_channel(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "channel_name")
        if err:
            return err
        channel_name = content["channel_name"]
        pub_remove_channel(did, app_id, channel_name)
        return self.response.response_ok()

    def get_pub_channels(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err

        channel_list = pub_get_pub_channels(did, app_id)
        if not channel_list:
            return self.response.response_err(NOT_FOUND, "not found channel of " + did)

        channel_name_list = list()
        for channel in channel_list:
            channel_name_list.append(channel[PUB_CHANNEL_NAME])

        data = {"channels": channel_name_list}
        return self.response.response_ok(data)

    def get_sub_channels(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err

        channel_list = pub_get_sub_channels(did, app_id)
        if not channel_list:
            return self.response.response_err(NOT_FOUND, "not found channel of " + did)

        channel_name_list = list()
        for channel in channel_list:
            channel_name_list.append(channel[PUB_CHANNEL_NAME])

        data = {"channels": channel_name_list}
        return self.response.response_ok(data)

    def subscribe_channel(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response,
                                                             "pub_did",
                                                             "pub_app_id",
                                                             "channel_name")
        if err:
            return err
        pub_did = content["pub_did"]
        pub_appid = content["pub_app_id"]
        channel_name = content["channel_name"]

        info = pub_get_channel(pub_did, pub_appid, channel_name)
        if not info:
            return self.response.response_err(NOT_FOUND,
                                              f"There is no channel:{channel_name} published by did:{pub_did}, appid:{pub_appid}")

        pub_add_subscriber(pub_did, pub_appid, channel_name, did, app_id)
        return self.response.response_ok()

    def unsubscribe_channel(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response,
                                                             "pub_did",
                                                             "pub_app_id",
                                                             "channel_name")
        if err:
            return err
        pub_did = content["pub_did"]
        pub_appid = content["pub_app_id"]
        channel_name = content["channel_name"]
        pub_remove_subscribe(pub_did, pub_appid, channel_name, did, app_id)
        return self.response.response_ok()

    def push_message(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response,
                                                             "channel_name",
                                                             "message")
        if err:
            return err
        channel_name = content["channel_name"]
        message = content["message"]
        info = pub_get_channel(did, app_id, channel_name)
        if not info:
            return self.response.response_err(NOT_FOUND,
                                              f"There is no channel:{channel_name} published by did:{did}, appid:{app_id}")
        pubsub_push_message(did, app_id, channel_name, message, datetime.utcnow().timestamp())
        return self.response.response_ok()

    def pop_messages(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response,
                                                             "pub_did",
                                                             "pub_app_id",
                                                             "channel_name",
                                                             "message_limit")
        if err:
            return err
        pub_did = content["pub_did"]
        pub_appid = content["pub_app_id"]
        channel_name = content["channel_name"]
        limit = int(content["message_limit"])
        message_list = sub_pop_messages(pub_did, pub_appid, channel_name, did, app_id, limit)
        data = {"messages": message_list}
        return self.response.response_ok(data)
