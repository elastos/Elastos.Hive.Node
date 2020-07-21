# Elastos Hive Node

## Install

Install mongodb and run mongodb

### Prerequisite and environment

First clone the git repository, then go to the root repository folder.
Create python virtual environment and install the prerequisite.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

After that you can run Hive node using the new created virtual env.

### Custom the Configuration

Config hive/settings.py for mongodb. like:

```python
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
```

## Run

```bash
python manage.py runserver
```

The server will run on url like: http://127.0.0.1:5000
