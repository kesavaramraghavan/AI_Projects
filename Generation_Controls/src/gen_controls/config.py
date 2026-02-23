from pydantic import BaseModel, Field
from typing import List

class GenerationConfig(BaseModel):
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_p: float = Field(1.0, gt=0.0, le=1.0)
    max_tokens: int = Field(200, gt=1, le=2000)
    frequency_penalty: float = Field(0.0, ge=0.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=0.0, le=2.0)
    stop: List[str] = []