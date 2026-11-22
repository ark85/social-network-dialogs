FROM python:3.12-alpine

WORKDIR /app

RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore zabbix-utils==2.0.5

COPY provision_host.py .

ENTRYPOINT ["python", "-u", "provision_host.py"]
