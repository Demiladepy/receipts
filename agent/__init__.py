"""Naive complaint agent. Heavy imports stay behind attribute access."""

__all__ = ["init_tracing", "investigate"]


def __getattr__(name: str):
    if name == "investigate":
        from agent.loop import investigate

        return investigate
    if name == "init_tracing":
        from agent.tracing import init_tracing

        return init_tracing
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
