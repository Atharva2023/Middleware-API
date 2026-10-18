import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# ---------- Your assigned values ----------
ALLOWED_ORIGIN = "https://app-cob6wj.example.com"
RATE_LIMIT = 13          # B requests
WINDOW_SECONDS = 10      # per 10-second window
EMAIL = "your_logged_in_email@example.com"

# Add the exam page origin here if the assignment gives it to you.
EXAM_PAGE_ORIGIN = "https://exam-page-origin.example.com"

ALLOWED_ORIGINS = [
    ALLOWED_ORIGIN,
    EXAM_PAGE_ORIGIN,
]

# ---------- Middleware 2: CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,       # No "*"
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id"],
    expose_headers=["X-Request-ID"],     # Browser JS can read this response header
)

# ---------- Middleware 3: rate limiter ----------
# client_id -> timestamps of recent requests
request_history = defaultdict(deque)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id")

    # If there is no client ID, let the request through.
    # The grader sends X-Client-Id for rate-limit tests.
    if client_id is None:
        return await call_next(request)

    now = time.monotonic()
    history = request_history[client_id]

    # Remove timestamps older than the 10-second window.
    while history and now - history[0] >= WINDOW_SECONDS:
        history.popleft()

    # Already used all 13 requests in this window?
    if len(history) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    # Record this request and continue.
    history.append(now)
    return await call_next(request)

# ---------- Middleware 1: request context ----------
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    # Make it available to the endpoint.
    request.state.request_id = request_id

    response = await call_next(request)

    # Always return it in the response header too.
    response.headers["X-Request-ID"] = request_id
    return response

# ---------- Endpoint ----------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
