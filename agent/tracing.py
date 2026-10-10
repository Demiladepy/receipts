"""neatlogs bootstrap. Import and call init_tracing() once at process start."""
import os

import neatlogs
from dotenv import load_dotenv


def init_tracing(workflow_name: str = "receipts-agent", tags: list[str] | None = None) -> None:
    load_dotenv()
    neatlogs.init(
        api_key=os.environ.get("NEATLOGS_API_KEY"),
        workflow_name=workflow_name,
        tags=tags or [],
    )
