FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install --no-cache-dir cherrypy mysql-connector-python pyyaml requests reportlab
RUN pip install --no-cache-dir -r requirements.txt

COPY eeapi.py .
COPY config.yml .
COPY ee_log.png .

CMD [ "python", "./eeapi.py" ]
