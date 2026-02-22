from pydantic import BaseModel

class EstimateRequest(BaseModel):
    prompt: str
    max_completion_tokens: int = 512

class EstimateResponse(BaseModel):
    prompt_tokens: int
    fits_context: bool
    estimated_max_cost_usd: float
    duration_ms: float