FROM ubuntu:14.04


RUN apt-get update -y
RUN apt-get install -y python-pip python-dev

ENV CELERY_BROKER_URL amqp://rabbit1 
ENV CELERY_RESULT_BACKEND amqp://rabbit1 
ENV C_FORCE_ROOT true

ENV HOST 0.0.0.0
ENV PORT 5000
ENV DEBUG true

COPY . /worker
WORKDIR /worker

# install requirements
RUN pip install -r requirements.txt

ENTRYPOINT celery -A jobs worker --loglevel=info --pool=solo
