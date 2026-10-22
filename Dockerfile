FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt && useradd --create-home appuser
COPY assistant.py web.py ./
COPY static ./static
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn web:app --host 0.0.0.0 --port \"$PORT\" --workers 1"]
