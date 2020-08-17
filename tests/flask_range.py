from datetime import datetime
from flask import Flask
from os import path

from hive.util.flask_rangerequest import RangeRequest

my_file = '/Users/wanghan/Downloads/movie/test.rmvb'
app = Flask(__name__)
size = path.getsize(my_file)
with open(my_file, 'rb') as f:
    etag = RangeRequest.make_etag(f)
last_modified = datetime.utcnow()


@app.route('/', methods=('GET', 'POST'))
def index():
    return RangeRequest(open(my_file, 'rb'),
                        etag=etag,
                        last_modified=last_modified,
                        size=size).make_response()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
