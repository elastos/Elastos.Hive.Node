# -*- coding: utf-8 -*-

"""
The settings for hive node, please use this instead of the hive.settings.
"""
from pathlib import Path

from hive.settings import hive_setting
from hive.util.common import did_tail_part


def st_get_vault_path(did):
    """
    Get the root dir of the vault.
    :param did: The user DID.
    :return: Path: the path of the vault root.
    """
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did)
    else:
        path = path.resolve() / did_tail_part(did)
    return path.resolve()


def st_get_ipfs_cache_path(did):
    """
    Get the root dir of the IPFS cache files.
    :param did: The user DID
    :return: Path: the path of the cache root.
    """
    return st_get_vault_path(did) / 'ipfs_cache'
