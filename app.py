from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI()
REQS = Counter("users_requests_total", "total", ["route"])
LAT  = Histogram("users_latency_seconds", "latency", ["route"])

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/users/{user_id}")
@LAT.labels("/users/{user_id}").time()
def get_user(user_id: str):
    REQS.labels("/users/{user_id}").inc()
    return {"id": user_id, "name": f"user-{user_id}"}

@app.get("/users")
@LAT.labels("/users").time()
def list_users():
    REQS.labels("/users").inc()
    return [{"id": "1", "name": "alice"}, {"id": "2", "name": "bob"}]