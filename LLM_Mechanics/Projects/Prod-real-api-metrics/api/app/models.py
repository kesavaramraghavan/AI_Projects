# Filename: models.py
from pydantic import BaseModel

class EstimateRequest(BaseModel):
    prompt: str
    max_completion_tokens: int = 1024