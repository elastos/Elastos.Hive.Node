# -*- coding: utf-8 -*-

"""
The settings for hive node, please use this instead of the hive.settings.
"""
from pathlib import Path

from src.settings import hive_setting
from src.utils_v1.common import did_tail_part


def _st_get_vault_path(user_did):
    """
    Get the root dir of the vault.
    :param user_did: The user DID.
    :return: Path: the path of the vault root.
    """
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(user_did)
    else:
        path = path.resolve() / did_tail_part(user_did)
    return path.resolve()


def st_get_ipfs_cache_path(user_did):
    """
    Get the root dir of the IPFS cache files.
    :param user_did: The user DID
    :return: Path: the path of the cache root.
    """
    return _st_get_vault_path(user_did) / 'ipfs_cache'
