#!/usr/bin/env python
# coding=utf-8

from flask_script import Server, Shell, Manager, Command, prompt_bool

from hive import create_app

app = create_app()
manager = Manager(app)
# manager.add_option('-c', '--config', dest='config', required=False)

if __name__ == "__main__":
    # app.run(debug=False)
    manager.run()
