import binascii
import hashlib

from datetime import datetime
from flask import Response, abort, request
from io import BytesIO
from werkzeug.http import parse_date, http_date

from ._utils import parse_range_header


class RangeRequest:

    def __init__(self,
                 data,
                 etag: str = None,
                 last_modified: datetime = None,
                 size: int = None) -> None:

        if not ((etag is None and last_modified is None and size is None) or
                (etag is not None and last_modified is not None and size is not None)):
            raise ValueError('Must specifiy all range data or none.')

        if isinstance(data, bytes):
            self.__data = BytesIO(data)
        elif isinstance(data, str):
            self.__data = BytesIO(data.encode('utf-8'))
        else:
            self.__data = data

        if etag is not None:
            self.__etag = etag
        else:
            self.__etag = self.make_etag(self.__data)
            self.__data.seek(0)

        if last_modified is not None:
            self.__last_modified = last_modified
        else:
            self.__last_modified = datetime.utcnow()

        if size is not None:
            self.__size = size
        else:
            # TODO this is stupid, but good enough for now
            self.__size = 0
            while True:
                chunk = self.__data.read(4096)
                if chunk:
                    self.__size += len(chunk)
                else:
                    break
            self.__data.seek(0)

    def make_response(self) -> Response:
        use_default_range = True
        status_code = 200
        # range requests are only allowed for get
        if request.method == 'GET':
            range_header = request.headers.get('Range')

            ranges = parse_range_header(range_header, self.__size)
            if not (len(ranges) == 1 and ranges[0][0] == 0 and ranges[0][1] == self.__size - 1):
                use_default_range = False
                status_code = 206

            if range_header:
                if_range = request.headers.get('If-Range')
                if if_range and if_range != self.__etag:
                    use_default_range = True
                    status_code = 200

        if use_default_range:
            ranges = [(0, self.__size - 1)]

        if len(ranges) > 1:
            abort(416)  # We don't support multipart range requests yet

        if_unmod = request.headers.get('If-Unmodified-Since')
        if if_unmod:
            if_date = parse_date(if_unmod)
            if if_date and if_date < self.__last_modified:
                status_code = 304

        # TODO If-None-Match support

        if status_code != 304:
            resp = Response(self.__generate(ranges, self.__data))
        else:
            resp = Response()

        if not use_default_range:
            etag = self.make_etag(BytesIO((self.__etag + str(ranges)).encode('utf-8')))
        else:
            etag = self.__etag

        resp.headers['Content-Length'] = ranges[0][1]+1 - ranges[0][0]
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['ETag'] = etag
        resp.headers['Last-Modified'] = http_date(self.__last_modified)

        if status_code == 206:
            resp.headers['Content-Range'] = \
                'bytes {}-{}/{}'.format(ranges[0][0], ranges[0][1], self.__size)

        resp.status_code = status_code

        return resp

    def __generate(self, ranges: list, readable):
        for (start, end) in ranges:
            readable.seek(start)
            bytes_left = end - start + 1

            chunk_size = 4096
            while bytes_left > 0:
                read_size = min(chunk_size, bytes_left)
                chunk = readable.read(read_size)
                bytes_left -= read_size
                yield chunk

        readable.close()

    @classmethod
    def make_etag(cls, data):
        hasher = hashlib.sha256()

        while True:
            read_bytes = data.read(4096)
            if read_bytes:
                hasher.update(read_bytes)
            else:
                break

        hash_value = binascii.hexlify(hasher.digest()).decode('utf-8')
        return '"sha256:{}"'.format(hash_value)
