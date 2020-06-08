Elastos Hive node based on [Eve](https://docs.python-eve.org/)
===

##Install

    Install mongodb and run mongodb

###Prerequisite

	pip install -r requirements.txt

###Custom the Configuration
	
	Config hive/settings.py for mongodb. like:
        ```
        MONGO_HOST = 'localhost'
        MONGO_PORT = 27017
        ```

###Run

	python manage.py runserver
	The server will run on url like: http://127.0.0.1:5000

