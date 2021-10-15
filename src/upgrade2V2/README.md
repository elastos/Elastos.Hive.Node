It is used to upgrade v1 to v2 APIs. When the v2 APIs work, you can just run them to transfer files. Assume 

1. If you start using v2 APIs, you will need to move the files from v1 to v2 since they will work for the end user.

1.1 Create the file metadata from v1 HIVE_DATA directory.

```shell script
$ python gen_files_metadata.py <HIVE_DATA>
```
    
1.2 Import files metadata to v2.

```shell script
$ python merge_files_change.py init <HIVE_DATA>/vaults.metadata.json
```

2. The vault files need to be synced from v1 to v2 when v1 ends.

1.1 Create the file metadata from v1 HIVE_DATA directory.

```shell script
$ python gen_files_metadata.py <HIVE_DATA>
```
    
1.2 Update file changes to v2.

```shell script
$ python merge_files_change.py update <HIVE_DATA>/vaults.metadata.json
```
