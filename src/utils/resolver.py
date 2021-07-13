# -*- coding: utf-8 -*-
from src.utils.http_client import HttpClient
from src.utils.http_exception import BadRequestException


class ElaResolver:
    def __init__(self, base_url):
        self.base_url = base_url
        self.cli = HttpClient()

    def get_transaction_info(self, transaction_id):
        param = {"method": "getrawtransaction", "params": [transaction_id, True]}
        json_body = self.cli.post(self.base_url, None, param, success_code=200)
        if not isinstance(json_body, dict) or json_body['error'] is not None:
            raise BadRequestException(msg=f'Failed to get transaction info by error: {json_body["error"]}')
        return json_body['result']

    def hexstring_to_bytes(self, s: str, reverse=True):
        if reverse:
            return bytes(reversed([int(s[x:x + 2], 16) for x in range(0, len(s), 2)]))
        else:
            return bytes([int(s[x:x + 2], 16) for x in range(0, len(s), 2)])
