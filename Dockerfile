FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto ./proto
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/echo.proto
COPY server.py .
ENV PORT=50051
ENV METRICS_PORT=9100
CMD ["python","server.py"]