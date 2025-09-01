import os, time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import redis
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_RPS = int(os.getenv("DEFAULT_RPS", "50"))
DEFAULT_BURST = int(os.getenv("DEFAULT_BURST", "100"))
WINDOW_SECONDS = int(os.getenv("WINDOW_SECONDS", "60"))
ENABLE_SLIDING = os.getenv("ENABLE_SLIDING_WINDOW", "true").lower() == "true"

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI()

REQS_TOTAL = Counter("rl_requests_total", "total", ["decision"])
TOKEN_GAUGE = Gauge("rl_tokens_available", "tokens", ["key"])
LATENCY = Histogram("rl_check_latency_seconds", "latency")

LUA_TOKEN_BUCKET = r.register_script("""
local key = KEYS[1]
local now = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local burst = tonumber(ARGV[3])
local data = redis.call("HMGET", key, "ts", "tokens")
local ts = tonumber(data[1])
local tokens = tonumber(data[2])
if not ts or not tokens then
  ts = now
  tokens = burst
end
local elapsed = math.max(0, now - ts)
local refill = (elapsed / 1000.0) * rate
tokens = math.min(burst, tokens + refill)
local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end
redis.call("HMSET", key, "ts", now, "tokens", tokens)
redis.call("PEXPIRE", key, 120000)
return {allowed, tokens}
""")

def token_bucket_allow(key: str, rps: int, burst: int):
    now_ms = int(time.time() * 1000)
    allowed, tokens = LUA_TOKEN_BUCKET(keys=[f"tb:{key}"], args=[now_ms, rps, burst])
    TOKEN_GAUGE.labels(key).set(float(tokens))
    return int(allowed) == 1

def sliding_window_allow(key: str, limit: int, window_s: int):
    now = time.time()
    keyz = f"sw:{key}"
    pipe = r.pipeline()
    pipe.zremrangebyscore(keyz, 0, now - window_s)
    pipe.zcard(keyz)
    pipe.execute()
    count = r.zcard(keyz)
    if count >= limit:
        return False
    r.zadd(keyz, {str(now): now})
    r.expire(keyz, window_s*2)
    return True

def decision_for(path: str, api_key: str):
    route = "grpc" if path.startswith("/grpc.") else "users"
    rps = int(r.get(f"cfg:rps:{api_key}:{route}") or DEFAULT_RPS)
    burst = int(r.get(f"cfg:burst:{api_key}:{route}") or DEFAULT_BURST)
    allowed = token_bucket_allow(f"{api_key}:{route}", rps, burst)
    if allowed and ENABLE_SLIDING:
        allowed = sliding_window_allow(f"{api_key}:{route}", limit=rps, window_s=WINDOW_SECONDS)
    return allowed

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/authorize")
@LATENCY.time()
async def authorize(req: Request):
    api_key = req.headers.get("x-api-key", "anon")
    path = req.headers.get("x-original-path", "/")
    allowed = decision_for(path, api_key)
    if allowed:
        REQS_TOTAL.labels("allow").inc()
        return JSONResponse(status_code=200, content={"ok": True}, headers={"x-rate-limit-remaining": "1", "x-rate-limit-reset": str(WINDOW_SECONDS)})
    else:
        REQS_TOTAL.labels("deny").inc()
        return JSONResponse(status_code=429, content={"ok": False, "reason": "rate_limited"})

@app.post("/admin/set_limit")
async def set_limit(payload: dict):
    api_key = payload.get("api_key", "anon")
    route = payload.get("route", "users")
    rps = int(payload.get("rps", DEFAULT_RPS))
    burst = int(payload.get("burst", DEFAULT_BURST))
    r.set(f"cfg:rps:{api_key}:{route}", rps)
    r.set(f"cfg:burst:{api_key}:{route}", burst)
    return {"ok": True, "api_key": api_key, "route": route, "rps": rps, "burst": burst}