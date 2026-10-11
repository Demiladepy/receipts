"""neatlogs bootstrap. Import and call init_tracing() once at process start."""

import os
import sys
from typing import Any

import neatlogs
from dotenv import load_dotenv


def init_tracing(
    workflow_name: str = "receipts-agent",
    tags: list[str] | None = None,
    *,
    disable_export: bool = False,
    tracer_provider: Any = None,
    register_shutdown_handlers: bool = True,
) -> None:
    load_dotenv()
    if not os.environ.get("NEATLOGS_API_KEY") and not disable_export:
        print("WARNING: NEATLOGS_API_KEY is empty; neatlogs export is disabled and no trace "
              "will reach the app. Set it in .env.", file=sys.stderr)
    kwargs: dict[str, Any] = {
        "api_key": os.environ.get("NEATLOGS_API_KEY"),
        "workflow_name": workflow_name,
        "tags": tags or [],
        "disable_export": disable_export,
        "register_shutdown_handlers": register_shutdown_handlers,
    }
    if tracer_provider is not None:
        kwargs["tracer_provider"] = tracer_provider
    neatlogs.init(**kwargs)
