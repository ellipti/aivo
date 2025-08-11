from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="AIVO Analyzer API")


class AnalyzeRequest(BaseModel):
    prompt: str


class AnalyzeResponse(BaseModel):
    result: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest):
    # Stubbed response; integrate OpenAI + guardrails later
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return {"result": f"Analyzed with {model}: {body.prompt[:50]}..."}

