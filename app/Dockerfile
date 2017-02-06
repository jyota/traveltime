FROM ubuntu:14.04


RUN apt-get update -y
RUN apt-get install -y python-pip python-dev

COPY . /app
WORKDIR /app

# install requirements
RUN pip install -r requirements.txt

ENV FLASK_HOST 0.0.0.0
ENV FLASK_PORT 5000
ENV FLASK_DEBUG true
ENV REDIS_URL redis://redis1:6379/0

