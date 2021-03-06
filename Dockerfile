# Pull base image.
FROM ubuntu:18.04

MAINTAINER Daigo Tanaka <daigo.tanaka@gmail.com>

# upgrade is not recommended by the best practice page
# RUN apt-get -y upgrade

# Never prompts the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive

# Define locale
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LC_CTYPE en_US.UTF-8
ENV LC_MESSAGES en_US.UTF-8

# Install dependencies via apt-get
# Note: Always combine apt-get update and install
RUN set -ex \
    && buildDeps=' \
        python-dev \
        python3-dev \
        libkrb5-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        build-essential \
        libblas-dev \
        liblapack-dev \
        libpq-dev \
    ' \
    && apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
        $buildDeps \
        sudo \
        apparmor-utils \
        python-setuptools \
        python-pip \
        python3-requests \
        python3-setuptools \
        python3-pip \
        apt-utils \
        curl \
        rsync \
        netcat \
        locales \
        wget \
        git \
        openssh-server \
        gdebi-core \
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

#        vim \
#        libmysqlclient-dev \
#         postgresql postgresql-contrib \
#         mysql-client \
#        mysql-server \


#######
#  Add tini
ENV TINI_VERSION v0.18.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

########
# SSH stuff

RUN mkdir -p /var/run/sshd

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
# Or do this?
# RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config

COPY . /app

RUN rm -fr /app/.env

RUN chmod 777 -R /app

WORKDIR /app

RUN pip3 install wheel
RUN pip3 install --no-cache-dir -e ./tap_rest_api
RUN pip3 install --no-cache-dir -e ./target-bigquery
RUN pip3 install -r requirements.txt
RUN chmod a+x /usr/local/bin/*

ENTRYPOINT [ "/tini", "--" ]
CMD python3 runner.py ${COMMAND:-default} -d ${DATA:-{}}
