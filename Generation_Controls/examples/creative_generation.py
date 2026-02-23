from gen_controls.service import generate_text
from gen_controls.presets import PRESETS

prompt = "Write three futuristic startup ideas involving AI and climate."

print(generate_text(prompt, PRESETS["creative_writer"]))