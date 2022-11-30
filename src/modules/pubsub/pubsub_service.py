from datetime import datetime

from flask import request, g

from src.utils.consts import COL_PUBSUB_USR_DID, COL_PUBSUB_APP_DID, COL_PUBSUB_NAME, COL_PUBSUB_CONTENT, COL_PUBSUB_SCRIPT_NAME, COL_PUBSUB
from src.utils.customize_dict import Dotdict
from src.utils.http_exception import InvalidParameterException, PubSubMessageNotFoundException
from src.utils.http_request import RV, RequestData
from src.modules.database.mongodb_client import MongodbClient
from src.modules.scripting.scripting import Scripting, Context
from src.modules.subscription.vault import VaultManager


class Message(Dotdict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next = -1

    def get_target_did(self):
        return self.get_content()['context']['target_did']

    def get_target_app_did(self):
        return self.get_content()['context']['target_app_did']

    def get_script_name(self):
        return self.script_name

    def get_content(self):
        return self.content

    def get_collections(self):
        return self.get_content()['body']['collections']

    def get_interval(self):
        return self.get_content()['body']['interval']

    def update_next(self, cur_t=None):
        cur_t = int(datetime.now().timestamp()) if not cur_t else cur_t
        self.next = cur_t + self.content['body']['interval']

    def get_next(self):
        return self.next

    def get_params(self, cur_t):
        return dict(map(lambda c: (f"{c['name']}_{c['field']}", cur_t - self.get_interval()), self.get_collections()))


class PubSubMessage:
    def __init__(self):
        self.mcli = MongodbClient()
        self.scripting = Scripting()

    @staticmethod
    def verify_message(json_body):
        if not json_body:
            raise InvalidParameterException('Invalid request body')

        Context.validate_data(RV.get_body().get_opt('context', dict, {}))

        type_ = RV.get_body().get('type', str)
        if type_ != 'countDocs':
            raise InvalidParameterException('Invalid type')

        cols = RV.get_body().get('body').validate('interval', int).get('collections', list)
        for col in cols:
            if not isinstance(col, dict):
                raise InvalidParameterException('Invalid collections')

            RequestData(**col).validate('name', str).validate('field', str).validate('inside', int)

    def add(self, name, json_body):
        context = Context(json_body.get('context', {}))
        json_body['context'] = {
            'target_did': context.get_target_did(),
            'target_app_did': context.get_target_app_did()
        }

        # add aggregated script
        executables, params = [], {}
        for col in json_body.get('body').get('collections'):
            executables.append({
                'name': col['name'],
                'type': 'count',
                'body': {
                    'collection': col["name"],
                    'filter': {col['field']: {'$gte': f'$params.{col["name"]}_{col["field"]}'}}
                }
            })

        script_name = f'__pubsub_{name}'
        self.scripting.register_script_internal(script_name, {'executable': {
                'name': 'aggregated',
                'type': 'aggregated',
                'body': executables
            }}, context.get_target_did(), context.get_target_app_did())

        # add a new message
        doc = {
            COL_PUBSUB_USR_DID: g.usr_did,
            COL_PUBSUB_APP_DID: g.app_did,
            COL_PUBSUB_NAME: name,
            COL_PUBSUB_CONTENT: json_body,
            COL_PUBSUB_SCRIPT_NAME: script_name
        }
        self.mcli.get_user_collection(g.usr_did, g.app_did, COL_PUBSUB).replace_one({COL_PUBSUB_NAME: name}, doc)

    def remove(self, name):
        col = self.mcli.get_user_collection(g.usr_did, g.app_did, COL_PUBSUB)
        filter_ = {
            COL_PUBSUB_USR_DID: g.usr_did,
            COL_PUBSUB_APP_DID: g.app_did,
            COL_PUBSUB_NAME: name
        }
        msg = col.find_one(filter_)
        if not msg:
            raise PubSubMessageNotFoundException()

        self.scripting.unregister_script(msg[COL_PUBSUB_SCRIPT_NAME], is_internal=True)
        col.delete_one(filter_)

    def get_all(self, name=None):
        return self.get_all_by_user(g.usr_did, g.app_did, name)

    def get_all_by_user(self, user_did, app_did, name=None, raw=True):
        filter_ = {}
        if name:
            filter_['name'] = name
        items = self.mcli.get_user_collection(user_did, app_did, COL_PUBSUB).find_many(filter_)
        if not items:
            return []
        elif raw:
            return items
        return list(map(lambda d: Message(d), items))

    def get_result(self, msg: Message, cur_t):
        """ get result items for pushing message. """
        result = self.scripting.run_script_url(msg.get_script_name(), msg.get_target_did(), msg.get_target_app_did(), msg.get_params(cur_t))
        items = []
        for k, v in result.items():
            if v['count'] > 0:
                items.append({k: v['count']})
        return items


class PubSubService:
    """ pub/sub service is a service to register message and get pushing messages.

    To get the pushing messages, please wait on the websocket.
    """
    def __init__(self):
        self.mcli = MongodbClient()
        self.vault_manager = VaultManager()
        self.message = PubSubMessage()

    def register_message(self, name):
        self.vault_manager.get_vault(g.usr_did).check_write_permission().check_storage_full()

        json_body = request.get_json(force=True, silent=True)
        PubSubMessage.verify_message(json_body)

        self.message.add(name, json_body)

    def unregister_message(self, name):
        self.message.remove(name)

    def get_messages(self, name=None):
        return {
            'messages': self.message.get_all(name)
        }
