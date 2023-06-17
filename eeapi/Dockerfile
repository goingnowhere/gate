FROM python:3

WORKDIR /usr/src/app

RUN /usr/local/bin/python -m pip install --upgrade pip
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY eeapi.py .
COPY config.yml .
COPY ee_log.png .

CMD [ "python", "./eeapi.py" ]
