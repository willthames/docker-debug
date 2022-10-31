FROM python:3.11.0-slim-buster


EXPOSE 6000 6000
CMD python /app/server.py
WORKDIR /app
COPY requirements.txt requirements.txt
RUN apt update && apt upgrade -y && apt install -y g++ build-essential
RUN pip install -r requirements.txt
USER 1000
COPY templates templates
COPY server.py server.py
COPY helloworld.txt helloworld.txt
COPY static static
COPY colour.py colour.py
