# -*- coding: utf-8 -*-

"""
Http exceptions definition.
"""
import json
import logging
import traceback
import typing as t

from bson import json_util
from flask import jsonify, request
from sentry_sdk import capture_exception


class HiveException(Exception):
    NO_INTERNAL_CODE = -1

    UNEXPECTED_INTERNAL_CODE = 2000
    FLASK_INTERNAL_CODE = 3000

    code: t.Optional[int] = None
    internal_code: t.Optional[int] = NO_INTERNAL_CODE

    def __init__(self, msg):
        self.msg = msg

    def get_error_response(self):
        return jsonify(self.get_error_dict()), self.code

    def get_error_dict(self):
        return HiveException.__get_error_dict(self.internal_code, self.msg)

    @staticmethod
    def get_flask_error_dict(msg):
        return HiveException.__get_error_dict(HiveException.FLASK_INTERNAL_CODE, msg)

    @staticmethod
    def __get_error_dict(internal_code, msg):
        if not isinstance(internal_code, int):
            # unexpected check: catch this specific issue.
            msg_ = f'Invalid v2 internal code: {str(type(internal_code))}, {str(internal_code)} {traceback.format_exc()}'
            logging.getLogger('get_error_dict').error(msg_)
            capture_exception(error=Exception(f'V2EC UNEXPECTED: {msg_}'))

        # 'internal_code' is optional
        internal_code = internal_code if isinstance(internal_code, int) else HiveException.UNEXPECTED_INTERNAL_CODE
        error = {"message": msg}
        if internal_code > -1:
            error['internal_code'] = internal_code

        return {"error": error}

    @staticmethod
    def get_success_response(data, is_download=False, is_code=False):
        if is_code:
            # Support user-defined http status code.
            assert type(data) is tuple and len(data) == 2
            data, code = data[0], data[1]
        else:
            code = HiveException.__get_success_http_code()
        json_data = data if is_download else (json.dumps(data, default=json_util.default) if data else '')
        return json_data, code

    @staticmethod
    def __get_success_http_code():
        codes = {
            'GET': 200,
            'PUT': 200,
            'PATCH': 200,
            'POST': 201,
            'DELETE': 204,
        }
        if request.method not in codes:
            return 400
        return codes[request.method]

    def __str__(self):
        return json.dumps(self.get_error_dict())


# BadRequestException


class BadRequestException(HiveException):
    INVALID_PARAMETER = 1
    BACKUP_IS_IN_PROCESS = 2
    ELADID_ERROR = 3

    code = 400
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='Bad request'):
        super().__init__(msg)


class InvalidParameterException(BadRequestException):
    internal_code = BadRequestException.INVALID_PARAMETER

    def __init__(self, msg='Invalid parameter'):
        super().__init__(msg)


class BackupIsInProcessingException(BadRequestException):
    internal_code = BadRequestException.BACKUP_IS_IN_PROCESS

    def __init__(self, msg='Backup is in process.'):
        super().__init__(msg)


class ElaDIDException(BadRequestException):
    internal_code = BadRequestException.ELADID_ERROR

    def __init__(self, msg):
        super().__init__(msg)


# UnauthorizedException


class UnauthorizedException(HiveException):
    code = 401
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='You are unauthorized to make this request.'):
        super().__init__(msg)


# ForbiddenException @deprecated


class ForbiddenException(HiveException):
    VAULT_FROZEN = 1

    code = 403
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='Forbidden'):
        super().__init__(msg)


class VaultFrozenException(ForbiddenException):
    internal_code = ForbiddenException.VAULT_FROZEN

    def __init__(self, msg='The vault is frozen and has not writen permission.'):
        super().__init__(msg)


# NotFoundException


class NotFoundException(HiveException):
    VAULT_NOT_FOUND = 1
    BACKUP_NOT_FOUND = 2
    SCRIPT_NOT_FOUND = 3
    COLLECTION_NOT_FOUND = 4
    PRICING_PLAN_NOT_FOUND = 5
    FILE_NOT_FOUND = 6
    ORDER_NOT_FOUND = 7
    RECEIPT_NOT_FOUND = 8
    APPLICATION_NOT_FOUND = 9

    code = 404
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='Not found'):
        super().__init__(msg)


class VaultNotFoundException(NotFoundException):
    internal_code = NotFoundException.VAULT_NOT_FOUND

    def __init__(self, msg='The vault can not be found.'):
        super().__init__(msg)


class BackupNotFoundException(NotFoundException):
    internal_code = NotFoundException.BACKUP_NOT_FOUND

    def __init__(self, msg='The backup service can not be found.'):
        super().__init__(msg)


class ApplicationNotFoundException(NotFoundException):
    internal_code = NotFoundException.APPLICATION_NOT_FOUND

    def __init__(self, msg="The user's application can not be found."):
        super().__init__(msg)


class ScriptNotFoundException(NotFoundException):
    internal_code = NotFoundException.SCRIPT_NOT_FOUND

    def __init__(self, msg='The script can not be found.'):
        super().__init__(msg)


class CollectionNotFoundException(NotFoundException):
    internal_code = NotFoundException.COLLECTION_NOT_FOUND

    def __init__(self, msg='The collection can not be found.'):
        super().__init__(msg)


class PricePlanNotFoundException(NotFoundException):
    internal_code = NotFoundException.PRICING_PLAN_NOT_FOUND

    def __init__(self, msg='The pricing plan can not be found.'):
        super().__init__(msg)


class FileNotFoundException(NotFoundException):
    internal_code = NotFoundException.FILE_NOT_FOUND

    def __init__(self, msg='The file can not be found.'):
        super().__init__(msg)


class OrderNotFoundException(NotFoundException):
    internal_code = NotFoundException.ORDER_NOT_FOUND

    def __init__(self, msg='The payment order can not be found.'):
        super().__init__(msg)


class ReceiptNotFoundException(NotFoundException):
    internal_code = NotFoundException.RECEIPT_NOT_FOUND

    def __init__(self, msg='The payment receipt can not be found.'):
        super().__init__(msg)


# AlreadyExistsException


class AlreadyExistsException(HiveException):
    code = 455
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='Already exists'):
        super().__init__(msg)


# InternalServerErrorException


class InternalServerErrorException(HiveException):
    code = 500
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='Internal server error'):
        super().__init__(msg)


# NotImplementedException


class NotImplementedException(HiveException):
    code = 501
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='Not implemented yet'):
        super().__init__(msg)


# InsufficientStorageException


class InsufficientStorageException(HiveException):
    code = 507
    internal_code = HiveException.NO_INTERNAL_CODE

    def __init__(self, msg='Insufficient storage.'):
        super().__init__(msg)
