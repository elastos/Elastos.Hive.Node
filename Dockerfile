FROM python:3.6
MAINTAINER kpachhai

ENV PYTHONUNBUFFERED 1

RUN apt-get update -y && \
    apt-get install build-essential libffi-dev -y

ADD requirements.txt /src/

WORKDIR /src

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ADD . /src/

ENV LD_LIBRARY_PATH="/src/hive/util/did/"

EXPOSE 5000

CMD [ "python3", "manage.py",  "runserver", "--host", "0.0.0.0" ]