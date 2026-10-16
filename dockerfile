ARG PYTHON_VERSION=3.10

FROM python:${PYTHON_VERSION}-slim

# Run as the non-root user so the compromised API can not control the container
RUN useradd --create-home --uid 10001 appuser

WORKDIR /restaurantprojectsiasun/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the API needs( .env is excluded by .dockerignore, the variables come from env_file )
COPY --chown=appuser:appuser dags/api ./dags/api
# The customer web page( served by FastAPI at / )
COPY --chown=appuser:appuser web ./web

ENV PYTHONPATH=/restaurantprojectsiasun/app/dags
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["fastapi", "run", "dags/api/API_write_data.py", "--host", "0.0.0.0", "--port", "8000"]
