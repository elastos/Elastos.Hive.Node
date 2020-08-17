from flask import request
from flask_script import Manager

from hive import create_app

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


application = Manager(app)
# application.add_option('-c', '--config', dest='config', required=False)

if __name__ == "__main__":
    # application.run(debug=False)
    application.run()
