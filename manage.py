import logging, logging.config, yaml

from flask import request
from flask_script import Manager, Server

from hive import create_app

logging.config.dictConfig(yaml.load(open('logging.conf'), Loader=yaml.FullLoader))
logfile = logging.getLogger('file')
log_console = logging.getLogger('console')
logfile.debug("Debug FILE")
log_console.debug("Debug CONSOLE")

app = create_app(config='production')


@app.before_request
def handle_chunking():
    """
    Sets the "wsgi.input_terminated" environment flag, thus enabling
    Werkzeug to pass chunked requests as streams; this makes the API
    compliant with the HTTP/1.1 standard.  The gunicorn server should set
    the flag, but this feature has not been implemented.
    """
    transfer_encoding = request.headers.get("Transfer-Encoding", None)
    if transfer_encoding == "chunked":
        request.environ["wsgi.input_terminated"] = True


manager = Manager(app)
manager.add_command("runserver", Server(host="0.0.0.0", port=5000))
# manager.add_option('-c', '--config', dest='config', required=False)

if __name__ == "__main__":
    # manager.run(debug=False)
    manager.run()
