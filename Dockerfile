FROM python:3.8.0-alpine3.10


EXPOSE 5000 5000
CMD python /app/server.py
WORKDIR /app
COPY requirements.txt requirements.txt
RUN apk add --no-cache --virtual .build-deps gcc libffi musl-dev && \
    pip install -r requirements.txt && \
    apk del .build-deps
USER 1000
COPY templates templates
COPY server.py server.py
COPY helloworld.txt helloworld.txt
COPY static static
COPY colour.py colour.py
