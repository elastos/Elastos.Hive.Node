Elastos Hive node based on [Eve](https://docs.python-eve.org/)
===

##Install
* Install python3.5 or latter
* Install mongodb and run mongodb
* Install rclone

###Prerequisite
	pip install -r requirements.txt

###Custom the Configuration
config is in hive/settings.py:
* Config mongodb. 
    ```
    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017
    ```
* Config save file dir 
    ```
    DID_FILE_DIR = "./did_file"
    ```
* Config rclone config file path
    ```
    RCLONE_CONFIG_FILE = "/.config/rclone/rclone.conf"
    ```

* set system environment variables LD_LIBRARY_PATH to hive/util/did/

###Run
	python manage.py runserver
	The server will run on url like: http://127.0.0.1:5000

