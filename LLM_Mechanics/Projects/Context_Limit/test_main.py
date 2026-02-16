from main import prepare_prompt_or_fallback

def test_prepare_prompt_direct_vs_summarized():
    instructions = "You are a helpful assistant."
    short_prompt = "Hi"
    res_short = prepare_prompt_or_fallback(short_prompt, instructions)
    assert res_short["mode"] == "direct"

    long_prompt = "long " * 2000
    res_long = prepare_prompt_or_fallback(long_prompt, instructions)
    assert res_long["mode"] in ("direct", "summarized")
