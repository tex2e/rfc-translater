FROM python:3.12

ENV PYTHONIOENCODING utf-8

WORKDIR /opt/app/

COPY requirements.txt /opt/app/
RUN pip install -r /opt/app/requirements.txt
