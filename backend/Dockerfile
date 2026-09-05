FROM python:3.12-slim

WORKDIR /app/backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY backend/entrypoint.sh ./entrypoint.sh
COPY challenge /app/challenge
RUN chmod +x ./entrypoint.sh

CMD ["./entrypoint.sh"]
