FROM python:3.8-slim-buster
WORKDIR /app

RUN apt-get update && apt-get -y install git curl && apt-get autoremove --yes && rm -rf /var/lib/{apt,dpkg,cache,log}/

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

RUN mkdir -p /config/cache
COPY config.yml /config/

COPY *.py /app/

CMD [ "python3", "app.py" , "/config/config.yml"]
