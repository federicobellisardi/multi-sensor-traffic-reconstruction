# build with
# docker build --tag slides . -f slides.docker

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

RUN apt update && apt upgrade -y 
RUN apt install cmake libboost-all-dev -y
RUN apt install libfltk1.3-dev -y

RUN mkdir /root/Code
ENV WORKSPACE /root/Code

COPY requirements.txt /root/Code/requirements.txt
RUN python3 -m pip install -r /root/Code/requirements.txt

RUN mkdir -p -m 700 /root/.ssh
COPY --chown=root:root .ssh/mover_rsa /root/.ssh/id_rsa
COPY --chown=root:root .ssh/mover_rsa.pub /root/.ssh/id_rsa.pub
RUN chmod 600 /root/.ssh/*
RUN ssh-keyscan -H github.com >> /root/.ssh/known_hosts

WORKDIR /root/Code
RUN git config --global user.name "gitmover" && git config --global user.email gitmover@gmail.com
RUN git clone git@github.com:physycom/sysconfig.git && git clone git@github.com:pybind/pybind11.git

ENV MOVER_VERSION "v1.2.4"
RUN \
  echo ${MOVER_VERSION} > /mover_version && \
  git clone git@github.com:physycom/covid_hep.git && \
  cd covid_hep && \
  git submodule update --init --recursive && \
  ./build.sh

RUN \
  cd /root/Code/covid_hep/ && \
  cp vars/conf/config.json.docker vars/conf/config.json && \
  cp dashboard/fastapi/sim-ws.py /app/main.py

COPY ./prestart.sh /app/prestart.sh
