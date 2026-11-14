FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY pyproject.toml ./
COPY app ./app
COPY config ./config
RUN pip install . && useradd -r -u 1000 sentinela && mkdir /data && chown sentinela /data
USER sentinela
ENV SENTINELA_DATABASE_URL=sqlite:////data/sentinela.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
