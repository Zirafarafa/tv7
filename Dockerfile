# Python 3.13 needs a newer lxml than the pinned 5.2.2 (no wheels).
FROM python:3.12-slim-trixie
WORKDIR /app

# curl is needed for the compose healthcheck.
RUN apt-get update && apt-get -y install --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

RUN mkdir -p /config/cache
COPY config.yml /config/

COPY *.py /app/

CMD [ "python3", "app.py" , "/config/config.yml"]
