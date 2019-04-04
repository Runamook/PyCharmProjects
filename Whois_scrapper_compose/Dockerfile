FROM python:3.6
ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
CMD ["python3" "scrapper_new.py", "use_database", "whois_scrapper.log", "postgres://root:manopc@corepo.org:5432/companies", "False"]
