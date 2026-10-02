FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . \
 && useradd --create-home agritech && mkdir -p /app/uploads && chown agritech /app/uploads
USER agritech
EXPOSE 8000
# Migrations first, then the API. Production: AGT_ENV=prod, AGT_AUTO_CREATE_SCHEMA=false, real secrets.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
