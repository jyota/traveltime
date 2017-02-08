FROM ubuntu:14.04


RUN apt-get update -y
RUN apt-get install -y supervisor nginx python-pip python-dev

RUN ln -sf /dev/stdout /var/log/nginx/access.log \
	&& ln -sf /dev/stderr /var/log/nginx/error.log
EXPOSE 80 443
# Finished setting up Nginx

RUN echo "daemon off;" >> /etc/nginx/nginx.conf

COPY nginx.conf /etc/nginx/conf.d/

COPY uwsgi.ini /etc/uwsgi/

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY . /app
WORKDIR /app

# install requirements
RUN pip install -r requirements.txt

ENV REDIS_URL redis://redis1:6379/0

