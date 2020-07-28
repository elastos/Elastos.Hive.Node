# Elastos Hive Node

##Install
* Install python3.5 or latter
* Install mongodb and run mongodb
* Install rclone

###Prerequisite and environment
First clone the git repository, then go to the root repository folder.
Create python virtual environment and install the prerequisite.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

After that you can run Hive node using the new created virtual env.

###Custom the Configuration
Configuration is in hive/settings.py:

* Config mongodb. 
```python
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
```

* Config save file dir 
```python
DID_FILE_DIR = "./did_file"
```

* Config rclone config file path
```python
RCLONE_CONFIG_FILE = "/.config/rclone/rclone.conf"
```

* set system environment variables LD_LIBRARY_PATH to hive/util/did/

### Run
```bash
python manage.py runserver
```

The server will run on url like: http://127.0.0.1:5000
