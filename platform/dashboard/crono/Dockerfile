FROM python:3.8

RUN mkdir /code
ENV WORKSPACE /code

COPY ./python  ${WORKSPACE}/
COPY requirements.txt ${WORKSPACE}/requirements.txt
RUN python3 -m pip install -r ${WORKSPACE}/requirements.txt
RUN apt-get update && apt-get -y install cron vim
WORKDIR /app

RUN \
  cd ${WORKSPACE}/ && \
  cp get-coils-api.py /app/get-coils-api.py  && \
  chmod a+x /app/get-coils-api.py
  
COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab
RUN touch /var/log/cron.log

CMD ["cron", "-f"]