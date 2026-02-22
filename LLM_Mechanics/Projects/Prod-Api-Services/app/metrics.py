from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "token_estimator_requests_total",
    "Total number of estimate requests"
)

REQUEST_LATENCY = Histogram(
    "token_estimator_request_latency_seconds",
    "Request latency in seconds"
)