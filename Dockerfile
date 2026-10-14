FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY policy.yaml .

RUN useradd -m tl && mkdir -p /srv/data /srv/weights && chown -R tl /srv
USER tl

ENV TL_MODEL_MODE=stub TL_AUDIT_DB=/srv/data/audit.db TL_WEIGHTS_DIR=/srv/weights
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
