from flask import request, g

from src.modules.database.mongodb_client import MongodbClient
from src.modules.scripting.scripting import Scripting, Context
from src.modules.subscription.vault import VaultManager
from src.utils.consts import COL_PUBSUB_USR_DID, COL_PUBSUB_APP_DID, COL_PUBSUB_NAME, COL_PUBSUB_CONTENT, COL_PUBSUB_SCRIPT_NAME, COL_PUBSUB
from src.utils.http_exception import InvalidParameterException, PubSubMessageNotFoundException
from src.utils.http_request import RV, RequestData, get_dict


class PubSubMessage:
    def __init__(self):
        self.mcli = MongodbClient()
        self.scripting = Scripting()

    @staticmethod
    def verify_message(json_body):
        if not json_body:
            raise InvalidParameterException('Invalid request body')

        Context.validate_data(RV.get_body().get_opt('context', dict))

        type_ = RV.get_body().get('type', str)
        if type_ != 'countDocs':
            raise InvalidParameterException('Invalid type')

        cols = RV.get_body().get('body.collections', list)
        for col in cols:
            RequestData(**get_dict(col)).validate('name', str).validate_opt('filter', dict)

        RV.get_body().validate('body.interval', int)

    def add(self, name, json_body):
        context = Context(json_body.get('context', {}))
        json_body['context'] = {
            'target_did': context.get_target_did(),
            'target_app_did': context.get_target_app_did()
        }

        # add aggregated script
        executables = []
        for col in json_body.get('body').get('collections'):
            executables.append({
                'name': col['name'],
                'type': 'count',
                'body': {
                    'collection': col["name"],
                    'filter': col.get('filter', {})
                }
            })

        script_name = f'__pubsub_{name}'
        self.scripting.register_script_internal(script_name, {'executable': {
                'name': 'aggregated',
                'type': 'aggregated',
                'body': executables
            }}, context.get_target_did(), context.get_target_app_did())

        # add a new message
        filter_ = {
            COL_PUBSUB_USR_DID: g.usr_did,
            COL_PUBSUB_APP_DID: g.app_did,
            COL_PUBSUB_NAME: name
        }
        update = {'$setOnInsert': {
            COL_PUBSUB_CONTENT: json_body,
            COL_PUBSUB_SCRIPT_NAME: script_name
        }}
        self.mcli.get_user_collection(g.usr_did, g.app_did, COL_PUBSUB).update_one(filter_, update, upsert=True)

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

        self.scripting.unregister_script(msg[COL_PUBSUB_SCRIPT_NAME])
        col.delete_one(filter_)

    def get_all(self, name=None):
        return self.get_all_by_user(g.usr_did, g.app_did, name)

    def get_all_by_user(self, user_did, app_did, name=None):
        filter_ = {}
        if name:
            filter_['name'] = name
        return self.mcli.get_user_collection(user_did, app_did, COL_PUBSUB).find_many(filter_)

    def get_result(self, msg):
        context = msg[COL_PUBSUB_SCRIPT_NAME]['context']
        result = self.scripting.run_script_url(msg[COL_PUBSUB_SCRIPT_NAME], context['target_did'], context['target_app_did'], {})
        return [{k: v['count']} for k, v in result.items()]


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
