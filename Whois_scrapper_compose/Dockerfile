FROM python:3.6
ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
CMD ["python", "scrapper_new.py", "./random.csv", "./logfile.log", "postgres://serp:serpserpserpserpserp@rpi.zvez.ga:5432/postgres"]
