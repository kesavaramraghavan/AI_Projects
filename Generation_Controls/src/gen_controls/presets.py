from .config import GenerationConfig

PRESETS = {
    "deterministic_tool": GenerationConfig(
        temperature=0.0,
        top_p=1.0,
        max_tokens=150,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\n\n"]
    ),
    "rag_qa": GenerationConfig(
        temperature=0.3,
        top_p=0.9,
        max_tokens=300,
        frequency_penalty=0.2,
        presence_penalty=0.0
    ),
    "creative_writer": GenerationConfig(
        temperature=0.9,
        top_p=0.95,
        max_tokens=400,
        frequency_penalty=0.3,
        presence_penalty=0.2
    ),
}