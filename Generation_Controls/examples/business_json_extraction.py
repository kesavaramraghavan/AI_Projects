from gen_controls.service import generate_text
from gen_controls.presets import PRESETS

prompt = """
Extract structured JSON and end with <END>.
Text: Order 4812 for Alice, Renton WA, total $39.80
"""

cfg = PRESETS["deterministic_tool"]
cfg.stop = ["<END>"]

print(generate_text(prompt, cfg))