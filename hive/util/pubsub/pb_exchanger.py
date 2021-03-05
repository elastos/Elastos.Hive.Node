# exchanger(in case for remote subscribing):setup  message subscriber, push data to  message subscriber
# 考虑远程 subscribe：是到publish的node来操作，还是在subscribe自己的node来操作
from hive.util.constants import PUB_CHANNEL_SUB_DID, PUB_CHANNEL_SUB_APPID
from hive.util.pubsub.publisher import pub_get_subscriber_list
from hive.util.pubsub.subscriber import sub_add_message


def pubsub_push_message(pub_did, pub_appid, channel_name, message, message_time):
    sub_list = pub_get_subscriber_list(pub_did, pub_appid, channel_name)
    for sub in sub_list:
        sub_add_message(pub_did,
                        pub_appid,
                        channel_name,
                        sub[PUB_CHANNEL_SUB_DID],
                        sub[PUB_CHANNEL_SUB_APPID],
                        message,
                        message_time)
