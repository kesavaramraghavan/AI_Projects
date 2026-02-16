from main import estimate_summarization_cost

def test_estimate_summarization_cost_basic():
    text = "This is a short meeting.\n" * 100
    stats = estimate_summarization_cost(text)
    assert stats["num_chunks"] >= 1
    assert stats["estimated_total_cost_usd"] >= 0.0
