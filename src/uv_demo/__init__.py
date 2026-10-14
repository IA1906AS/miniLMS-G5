from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Demo CI FastAPI App", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    message: str


class AddRequest(BaseModel):
    a: float
    b: float


class AddResponse(BaseModel):
    a: float
    b: float
    result: float


@app.get("/", response_model=HealthResponse)
def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "FastAPI CI Service is healthy"}


@app.post("/add", response_model=AddResponse)
def calculate_add(data: AddRequest) -> dict[str, float]:
    return {"a": data.a, "b": data.b, "result": data.a + data.b}


def main() -> None:
    import uvicorn

    uvicorn.run("uv_demo:app", host="127.0.0.1", port=8000, reload=True)
