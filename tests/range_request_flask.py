from datetime import datetime
from flask import Flask
from flask_rangerequest import RangeRequest
from os import path

import os

file_name = os.path.abspath('tests/range_request_flask.py')
app = Flask(__name__)
size = path.getsize(file_name)
with open(file_name, 'rb') as f:
    etag = RangeRequest.make_etag(f)
last_modified = datetime.utcnow()


@app.route('/', methods=('GET', 'POST'))
def index():
    return RangeRequest(open(file_name, 'rb'),
                        etag=etag,
                        last_modified=last_modified,
                        size=size).make_response()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
