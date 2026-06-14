import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """
    Custom Formatter that outputs logs in JSON format.
    Ensures easy parsing for metrics dashboards and production logging.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line_number": record.lineno
        }
        
        # Attach exception trace if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
            
        # Add extra properties passed to logger (e.g., logger.info("msg", extra={"key": "val"}))
        if hasattr(record, "extra_attrs") and isinstance(record.extra_attrs, dict):  # type: ignore
            log_payload.update(record.extra_attrs)  # type: ignore
            
        return json.dumps(log_payload)

def setup_logging(log_level: str = "INFO") -> None:
    """Configures root logger with custom JSON Formatter."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Remove default handlers to prevent duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Standard output stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(stream_handler)
    
    # Set logging level for libraries we don't want flooding stdout
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
