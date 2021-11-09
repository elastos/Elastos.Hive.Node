It's for upgrading to v2.4.1 from the previous version. The following steps need be executed before v2.4.1 working.

1. Initialize the files metadata of the vaults.

```shell script
$ cd <SOURCE_ROOT>/src/upgrade2V2
$ PYTHONPATH="${PYTHONPATH}:<SOURCE_ROOT>" python3 gen_files_metadata.py <HIVE_DATA>
```

2. Import files metadata to move files to IPFS node.

```shell script
$ PYTHONPATH="${PYTHONPATH}:<SOURCE_ROOT>" python merge_files_metadata.py init <HIVE_DATA>
```
