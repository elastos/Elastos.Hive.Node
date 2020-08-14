FROM python:3.6

ADD requirements.txt /src/
RUN cd /src && pip install -r requirements.txt

ADD . /src/
WORKDIR /src

ENV LD_LIBRARY_PATH="/src/hive/util/did/"

RUN cat /src/hive/util/did/__init__.py

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:application"]
