from __future__ import annotations

import logging
import os
import sys


class KVFormatter(logging.Formatter):
    """Formatter that appends common extra fields if present.

    Keeps classic human-readable format while surfacing structured context.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        keys = (
            "type",
            "action",
            "event",
            "user_id",
            "chat_id",
            "order_id",
            "bid_id",
            "category",
            "zone",
            "decision",
            "status",
            "media_count",
            "bids_count",
            "orders_count",
            "masters_count",
            "role",
            "count",
            "len",
            "back_to",
            "state",
            "has_ref",
            "text",
            "data",
            "took_ms",
        )
        parts: list[str] = []
        for k in keys:
            if hasattr(record, k):
                v = getattr(record, k)
                if v is None:
                    continue
                if k in {"text", "data"}:
                    parts.append(f"{k}={v!r}")
                else:
                    parts.append(f"{k}={v}")
        if parts:
            return f"{base} | {' '.join(parts)}"
        return base


essential_format = "% (asctime)s %(levelname)s %(name)s: %(message)s".replace(" ", " ")


def configure_logging(level: str | int | None = None) -> logging.Logger:
    """Configure root logger with KVFormatter. Safe to call multiple times."""
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    root = logging.getLogger()
    root.setLevel(level)

    # Drop existing handlers to avoid duplicates on reloads
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    formatter = KVFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Tweak noisy loggers if needed
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiogram.event").setLevel(logging.INFO)

    return root
