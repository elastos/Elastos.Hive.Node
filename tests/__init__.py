# -*- coding: utf-8 -*-
import os

from bson import ObjectId
from bson.errors import InvalidId

from src.utils.did.did_init import init_did_backend


def init_test():
    init_did_backend()


def is_valid_object_id(oid: str):
    try:
        ObjectId(oid)
        return True
    except (InvalidId, TypeError):
        return False


def test_log(*args, **kwargs):
    """ Just for debug, if try test API, please set environment::

        TEST_DEBUG=True

    """
    if os.environ.get('TEST_DEBUG') == 'True':
        print(*args, **kwargs)
