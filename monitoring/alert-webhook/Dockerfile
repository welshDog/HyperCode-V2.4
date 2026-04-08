FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt /build/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r /build/requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 10001 appuser

COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY app.py /app/app.py
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
