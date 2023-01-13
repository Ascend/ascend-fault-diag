# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
From ubuntu:20.04

RUN useradd -d /home/ma-user -u 1000 -m -s /bin/bash ma-user

RUN cp -a /etc/apt/sources.list /etc/apt/sources.list.bak && \
    sed -i "s@http://.*.ubuntu.com@http://repo.huaweicloud.com@g" /etc/apt/sources.list && \
    apt update && \
    apt install python3.8 python3-pip-y

RUN pip3 config set global.index-url https://mirrors.huaweicloud.com/repository/pypi/simple

RUN mkdir /home/ma-user/job && chown ma-user:ma-user -R /home/ma-user/job

COPY --chown=ma-user:ma-user . /home/ma-user/job

RUN cd /home/ma-user/jobn/py && pip3 install *.whl

RUN cd /home/ma-user/job/jre && \
    tar -zxvf jre-*.tar.gz

ENV JAVA_HOME=/home/ma-user/job/jre/jre1.8.0_332
ENV PATH=$JAVA_HOME/bin:$PATH

WORKDIR /home/ma-user/job
USER ma-user