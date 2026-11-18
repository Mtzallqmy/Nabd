FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN groupadd --system nabd && useradd --system --gid nabd nabd \
    && mkdir /app/data && chown nabd:nabd /app/data
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

USER nabd
EXPOSE 8080
CMD ["python", "-m", "app.main"]
