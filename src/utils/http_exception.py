# -*- coding: utf-8 -*-

"""
Http exceptions definition.
"""
import json

from bson import json_util
from flask import jsonify, request


class HiveException(Exception):
    NO_INTERNAL_CODE = -1

    def __init__(self, code, internal_code, msg):
        self.code = code
        self.internal_code = internal_code
        self.msg = msg

    def get_error_response(self):
        return jsonify(self._get_error_dict()), self.code

    def _get_error_dict(self):
        error = {"message": self.msg}
        if self.internal_code > 0:
            error['internal_code'] = self.internal_code
        return {"error": error}

    @staticmethod
    def get_success_response(data, is_download=False, is_code=False):
        code = HiveException.__get_success_http_code()
        if is_code:
            # Support user-defined http status code.
            assert type(data) is tuple and len(data) == 2
            data, code = data[0], data[1]
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
        assert request.method in codes
        return codes[request.method]

    def __str__(self):
        return json.dumps(self._get_error_dict())


# BadRequestException
# TODO: refine default and INVALID_PARAMETER for more specific ones.


class BadRequestException(HiveException):
    INVALID_PARAMETER = 1
    BACKUP_IS_IN_PROCESSING = 2

    def __init__(self, internal_code=INVALID_PARAMETER, msg='Invalid parameter'):
        super().__init__(400, internal_code, msg)


class InvalidParameterException(BadRequestException):
    def __init__(self, msg='Invalid parameter'):
        super().__init__(super().INVALID_PARAMETER, msg=msg)


class BackupIsInProcessingException(BadRequestException):
    def __init__(self, msg='Backup is in processing.'):
        super().__init__(super().BACKUP_IS_IN_PROCESSING, msg=msg)


# UnauthorizedException


class UnauthorizedException(HiveException):
    def __init__(self, msg='You are unauthorized to make this request.'):
        super().__init__(401, super().NO_INTERNAL_CODE, msg)


# ForbiddenException
# TODO: remove for vault accessing because no need active before using vault.


class ForbiddenException(HiveException):
    def __init__(self, msg='Forbidden.'):
        super().__init__(403, super().NO_INTERNAL_CODE, msg)


# NotFoundException


class NotFoundException(HiveException):
    VAULT_NOT_FOUND = 1
    BACKUP_NOT_FOUND = 2
    SCRIPT_NOT_FOUND = 3
    COLLECTION_NOT_FOUND = 4
    PRICE_PLAN_NOT_FOUND = 5
    FILE_NOT_FOUND = 6
    ORDER_NOT_FOUND = 7
    RECEIPT_NOT_FOUND = 8

    def __init__(self, internal_code=VAULT_NOT_FOUND, msg='The vault can not be found or is not activate.'):
        super().__init__(404, internal_code, msg)


class VaultNotFoundException(NotFoundException):
    def __init__(self, msg='The vault can not be found.'):
        super().__init__(internal_code=NotFoundException.VAULT_NOT_FOUND, msg=msg)


class BackupNotFoundException(NotFoundException):
    def __init__(self, msg='The backup service can not be found.'):
        super().__init__(internal_code=NotFoundException.BACKUP_NOT_FOUND, msg=msg)


class ApplicationNotFoundException(NotFoundException):
    def __init__(self, msg='The application of the user can not be found.'):
        super().__init__(internal_code=NotFoundException.BACKUP_NOT_FOUND, msg=msg)


class ScriptNotFoundException(NotFoundException):
    def __init__(self, msg='The script can not be found.'):
        super().__init__(internal_code=NotFoundException.SCRIPT_NOT_FOUND, msg=msg)


class CollectionNotFoundException(NotFoundException):
    def __init__(self, msg='The collection can not be found.'):
        super().__init__(internal_code=NotFoundException.COLLECTION_NOT_FOUND, msg=msg)


class PricePlanNotFoundException(NotFoundException):
    def __init__(self, msg='The price plan can not be found.'):
        super().__init__(internal_code=NotFoundException.PRICE_PLAN_NOT_FOUND, msg=msg)


class FileNotFoundException(NotFoundException):
    def __init__(self, msg='The file can not be found.'):
        super().__init__(internal_code=NotFoundException.FILE_NOT_FOUND, msg=msg)


class OrderNotFoundException(NotFoundException):
    def __init__(self, msg='The order can not be found.'):
        super().__init__(internal_code=NotFoundException.ORDER_NOT_FOUND, msg=msg)


class ReceiptNotFoundException(NotFoundException):
    def __init__(self, msg='The receipt can not be found.'):
        super().__init__(internal_code=NotFoundException.RECEIPT_NOT_FOUND, msg=msg)


# AlreadyExistsException


class AlreadyExistsException(HiveException):
    def __init__(self, msg='Already exists.'):
        super().__init__(455, super().NO_INTERNAL_CODE, msg)


# InternalServerErrorException


class InternalServerErrorException(HiveException):
    def __init__(self, msg='Internal server error.'):
        super().__init__(500, super().NO_INTERNAL_CODE, msg)


# NotImplementedException


class NotImplementedException(HiveException):
    def __init__(self, msg='Not implemented yet.'):
        super().__init__(501, super().NO_INTERNAL_CODE, msg)


# InsufficientStorageException


class InsufficientStorageException(HiveException):
    def __init__(self, msg='Insufficient storage.'):
        super().__init__(507, super().NO_INTERNAL_CODE, msg)
