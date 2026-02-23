from gen_controls.service import generate_text
from gen_controls.config import GenerationConfig

cfg = GenerationConfig(
    temperature=0.7,
    top_p=0.9,
    max_tokens=150,
    frequency_penalty=0.3,
    presence_penalty=0.1,
    stop=["\n\n"]
)

prompt = "Explain nucleus sampling in simple terms."

print(generate_text(prompt, cfg))