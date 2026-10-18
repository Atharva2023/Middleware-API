
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "25f1002516@ds.study.iitm.ac.in"
ALLOWED_ORIGINS = [
    "https://app-cob6wj.example.com",
    # Add the actual exam-page origin here if it is different.
]

RATE_LIMIT = 13
WINDOW_SECONDS = 10

app = FastAPI(title="Middleware Assignment")

# Per-client sliding-window request tracking.
client_requests = defaultdict(deque)
rate_lock = Lock()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Let browser CORS preflight requests through.
    if request.method == "OPTIONS":
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.monotonic()

    with rate_lock:
        timestamps = client_requests[client_id]

        while timestamps and now - timestamps[0] >= WINDOW_SECONDS:
            timestamps.popleft()

        if len(timestamps) >= RATE_LIMIT:
            retry_after = max(
                1,
                int(WINDOW_SECONDS - (now - timestamps[0]) + 0.999),
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)

    return await call_next(request)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# CORS must use explicit origins, never "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type", "Authorization"],
    expose_headers=["X-Request-ID", "Retry-After"],
)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


@app.get("/")
async def root():
    return {"status": "ok", "service": "middleware-api"}
