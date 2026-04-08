from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class SmokeRunConfig(BaseModel):
    env: Literal["dev", "staging", "production"] = "dev"

    orchestrator_url: HttpUrl = "http://127.0.0.1:8081"
    core_url: HttpUrl = "http://127.0.0.1:8000"
    dashboard_url: Optional[HttpUrl] = "http://127.0.0.1:8088"
    healer_url: Optional[HttpUrl] = "http://127.0.0.1:8010"
    redis_url: Optional[str] = None

    smoke_api_key: str = Field(default="", repr=False)
    smoke_mode_header_required: bool = True

    timeout_seconds: float = 5.0
    retries: int = 2
    retry_backoff_seconds: float = 0.2
    concurrency: int = 16
    verify_no_task_history_pollution: bool = True
    verify_no_redis_writes: bool = False

    output_dir: Path = Path("artifacts/smoke")
    write_markdown: bool = True
    write_junit: bool = True
    write_json: bool = True

    def safe_output_dir(self) -> Path:
        return Path(self.output_dir)
