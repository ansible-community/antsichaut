FROM python:3.10-slim

WORKDIR /usr/src/app

RUN pip install antsichaut

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]

