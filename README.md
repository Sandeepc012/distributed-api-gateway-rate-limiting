# Distributed API Gateway with Intelligent Rate Limiting

This project demonstrates a containerized API gateway architecture built with Envoy Proxy, gRPC and REST microservices, a Redis‑backed rate limiter, and Prometheus monitoring. It showcases how to handle high concurrency, apply adaptive rate limiting, and expose detailed metrics for observability.

## Features

- **Envoy gateway** configured for HTTP/2, gRPC routing, retry policies, circuit breakers, and outlier detection.
- **External authorization filter** that calls a FastAPI rate limiter implementing token bucket and optional sliding window algorithms.
- **gRPC echo service** and **FastAPI users service** instrumented with Prometheus counters and histograms.
- **Centralized docker-compose deployment** including Redis and Prometheus for metrics collection.

## Running the stack

To launch the entire system locally, run:

```bash
docker compose up --build
```

The services will be available through the Envoy gateway on `http://localhost:8080`, and Prometheus will be available at `http://localhost:9090`.

### REST Endpoints

The `users-api` service exposes simple REST endpoints:

- `GET /users` – returns a list of users
- `GET /users/{id}` – returns a single user by id

These endpoints must be called through the gateway with an `x-api-key` header (the default key is `anon` if not provided).

### gRPC Service

The `echo-grpc` service exposes an `EchoService` with a single `Say` method. It can be invoked via the gateway using any gRPC client.

### Rate Limiting

The rate limiter enforces per‑route limits using token bucket and optional sliding window algorithms. Limits can be adjusted on the fly by calling the admin endpoint on the rate limiter service:

```bash
curl -X POST http://localhost:8000/admin/set_limit \
  -H "Content-Type: application/json" \
  -d '{"api_key":"demo","route":"users","rps":10,"burst":20}'
```

This project is intended as a reference implementation for building scalable, observable API gateways with dynamic rate control.