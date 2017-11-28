FROM alpine:3.4
MAINTAINER toolbox@cloudpassage.com

RUN apk add --no-cache \
    git=2.8.6-r0 \
    python=2.7.12-r0 \
    py-pip=8.1.2-r0

RUN mkdir /app
COPY ./ /app/

WORKDIR /app/

RUN pip install pytest==2.8.0 \
    pytest-flake8==0.1 \
    pytest-cov==2.5.1 \
    coverage==4.2 \
    codeclimate-test-reporter==0.2.0

RUN pip install -e .

RUN /usr/bin/python -mpy.test --cov=haloscans || /usr/bin/python -mpy.test

RUN git branch -v
