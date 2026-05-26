FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements*.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt 2>/dev/null || pip install \
        fastapi uvicorn sqlalchemy asyncpg psycopg2-binary redis \
        pandas numpy scikit-learn joblib python-multipart pydantic

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
