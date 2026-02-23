from fastapi import FastAPI
from gen_controls.service import generate_text
from gen_controls.config import GenerationConfig

app = FastAPI()

@app.post("/generate")
def generate(req: GenerationConfig, prompt: str):
    return generate_text(prompt, req)