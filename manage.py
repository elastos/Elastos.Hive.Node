import logging.config, yaml

from flask import request
from flask_script import Manager, Server

from hive import create_app

logging.config.dictConfig(yaml.load(open('logging.conf'), Loader=yaml.FullLoader))
logfile = logging.getLogger('file')
log_console = logging.getLogger('console')
logfile.debug("Debug FILE")
log_console.debug("Debug CONSOLE")




manager = Manager(create_app)
manager.add_command("runserver", Server(host="0.0.0.0", port=5000))
manager.add_option('-c', '--config', dest='mode', required=False)

if __name__ == "__main__":
    # manager.run(debug=False)
    manager.run()
