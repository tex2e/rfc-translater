FROM python:3.12

ENV PYTHONIOENCODING utf-8

WORKDIR /opt/app/

RUN adduser --disabled-login mako && chown -R mako /opt/app/
USER mako

COPY requirements.txt /opt/app/
RUN pip install -r /opt/app/requirements.txt
COPY scraping-app/exec.py /opt/app/

CMD ["python", "exec.py"]
