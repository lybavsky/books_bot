FROM python:3.8

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/

ADD . .

ARG DATA_DIR=/data
ARG BOOKS_DIR=/books
ARG TG_TOKEN=""
ARG ES_HOST="127.0.0.1"

ENV DATA_DIR=/data
ENV BOOKS_DIR=/books

VOLUME /data
VOLUME /books

RUN pip3 install -r requirements.txt

RUN mkdir -p /data/covers_dir

RUN python3 manage.py makemigrations

EXPOSE 8000

CMD python3 manage.py migrate && python3 app.py
