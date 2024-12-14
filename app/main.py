from fastapi import FastAPI, Request, Response
from redis import Redis
import time
from json import loads, dumps
from starlette.middleware.base import _StreamingResponse
app = FastAPI()

r = Redis(
    host='redis-stack',
    port=6379,
)

@app.middleware("http")
async def caching_middleware(request: Request, call_next):
    rk = f"{request.method}::{request.base_url}::{request.query_params}::{request.url.path}"

    if request.url.path not in ['/docs', '/redoc', '/favicon.ico', '/openapi.json']:
        cached_value = read_redis(rk)
        if cached_value:
            print('cached value found')
            print(cached_value)
            return Response(
                content=cached_value, 
                status_code=200,
                headers=dict(request.headers),
                media_type="application/json"
            )

    start_time = time.time()
    response: _StreamingResponse = await call_next(request)


    if request.url.path not in ['/docs', '/redoc', '/favicon.ico', '/openapi.json']:
        if response.status_code == 200:
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
            response_body = b''.join(chunks)
            print('writing to redis')
            print(response_body.decode())
            write_redis(rk, response_body.decode())

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return Response(
        content=response_body, 
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type
    )


@app.get("/")
async def calc_fib(n: int):
    return {"message": fib(n)}

def write_redis(key: str, value: dict) -> bool:
    r.json().set(key, "$", dumps(value))
    return True

def read_redis(key: str):
    v = r.json().get(key, "$")
    if v:
        return loads(v[0])
    return

def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n-1) + fib(n-2)
