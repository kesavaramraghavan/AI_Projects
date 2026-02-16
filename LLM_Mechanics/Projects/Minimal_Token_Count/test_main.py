from utils import Tokenizer, fits_context, estimate_cost

def test_count_tokens_non_empty():
    tokenizer = Tokenizer()
    assert tokenizer.count_tokens("hello world") > 0

def test_estimate_cost_monotonic():
    c1 = estimate_cost(1000, 0)
    c2 = estimate_cost(2000, 0)
    assert c2 > c1

def test_fits_context_simple():
    assert fits_context(1000, 1000, 8000) is True
    assert fits_context(8000, 1, 8000) is False
