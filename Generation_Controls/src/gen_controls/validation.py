def enforce_bounds(cfg):
    if cfg.max_tokens > 1000:
        cfg.max_tokens = 1000
    return cfg