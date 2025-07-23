FROM python:3.10-slim

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1


COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn azure-identity
RUN pip install --no-cache-dir supervisor

# Redis
RUN apt-get update && apt-get install -y redis-server

WORKDIR /app
COPY . /app

COPY entrypoint.sh /app/entrypoint.sh
RUN apt-get update && apt-get install -y dos2unix && dos2unix /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh


RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser


ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/usr/local/bin/supervisord", "-c", "/app/supervisord.conf"]