"""
API Query Logger for LightRAG - Logs only API endpoint queries and responses.
Separate from the main query logger to focus specifically on /query and /query/stream endpoints.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import logging.handlers

from lightrag.utils import logger as lightrag_logger


class APIQueryLogger:
    """
    Simple rotating file logger specifically for API queries and responses.
    Logs only the essential query/response data from /query and /query/stream endpoints.
    """

    def __init__(
        self,
        log_file_path: str = "lightrag_api_queries.log",
        max_file_size_bytes: int = 2 * 1024 * 1024,  # 2 MB
        backup_count: int = 10,
    ):
        """
        Initialize the API query logger.

        Args:
            log_file_path: Path to the main log file
            max_file_size_bytes: Maximum size before rotation (default: 2MB)
            backup_count: Number of backup files to keep (default: 10)
        """
        self.log_file_path = Path(log_file_path)
        self.max_file_size_bytes = max_file_size_bytes
        self.backup_count = backup_count

        # Ensure log directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Statistics
        self.stats = {
            "total_api_queries": 0,
            "total_api_errors": 0,
            "start_time": datetime.now().isoformat(),
        }

        lightrag_logger.info(f"APIQueryLogger initialized: {self.log_file_path}")

    async def log_api_query(
        self,
        query_text: str,
        response_text: str,
        endpoint: str,  # "/query" or "/query/stream"
        query_mode: str = "unknown",
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        request_params: Optional[Dict[str, Any]] = None,
        is_streaming: bool = False,
    ):
        """
        Log an API query and its response.

        Args:
            query_text: The user's query
            response_text: The generated response (or "[Streaming Response]" for streams)
            endpoint: The API endpoint used ("/query" or "/query/stream")
            query_mode: The query mode (local, global, hybrid, etc.)
            response_time_ms: Response generation time in milliseconds
            error_message: Error message if query failed
            request_params: Original request parameters
            is_streaming: Whether this was a streaming response
        """
        async with self._lock:
            # Check if rotation is needed
            await self._check_rotation()

            # Build log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "endpoint": endpoint,
                "query": query_text,
                "response": response_text,
                "query_mode": query_mode,
                "is_streaming": is_streaming,
                "success": error_message is None,
                "response_time_ms": response_time_ms,
                "error": error_message,
            }

            # Add request parameters if provided (optional)
            if request_params:
                log_entry["request_params"] = {
                    "mode": request_params.get("mode"),
                    "top_k": request_params.get("top_k"),
                    "response_type": request_params.get("response_type"),
                    "only_need_context": request_params.get("only_need_context"),
                    "only_need_prompt": request_params.get("only_need_prompt"),
                }

            # Write to file
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

                # Update statistics
                self.stats["total_api_queries"] += 1
                if error_message:
                    self.stats["total_api_errors"] += 1

            except Exception as e:
                lightrag_logger.error(f"Failed to write API query log: {e}")

    async def _check_rotation(self):
        """Check if log rotation is needed and perform if necessary."""
        if not self.log_file_path.exists():
            return

        file_size = self.log_file_path.stat().st_size
        if file_size >= self.max_file_size_bytes:
            await self._rotate_logs()

    async def _rotate_logs(self):
        """Rotate log files."""
        lightrag_logger.info(f"Rotating API query logs: {self.log_file_path}")

        # Shift existing backup files
        for i in range(self.backup_count - 1, 0, -1):
            old_backup = self.log_file_path.with_suffix(f".{i}.log")
            new_backup = self.log_file_path.with_suffix(f".{i + 1}.log")
            if old_backup.exists():
                if i == self.backup_count - 1:
                    # Remove the oldest backup
                    old_backup.unlink()
                else:
                    old_backup.rename(new_backup)

        # Rename current log to .1.log
        if self.log_file_path.exists():
            self.log_file_path.rename(self.log_file_path.with_suffix(".1.log"))

    async def get_statistics(self) -> Dict[str, Any]:
        """Get API query logger statistics."""
        async with self._lock:
            stats = self.stats.copy()

            # Add current file info
            if self.log_file_path.exists():
                stats["current_file_size_mb"] = self.log_file_path.stat().st_size / (
                    1024 * 1024
                )
                stats["current_file_path"] = str(self.log_file_path)

            # Count backup files
            backup_count = sum(
                1
                for i in range(1, self.backup_count + 1)
                if self.log_file_path.with_suffix(f".{i}.log").exists()
            )
            stats["backup_files_count"] = backup_count

            return stats


# Singleton instance management
_api_query_logger_instance: Optional[APIQueryLogger] = None
_api_query_logger_lock = asyncio.Lock()


async def get_api_query_logger(
    log_file_path: str = "lightrag_api_queries.log",
    max_file_size_bytes: int = 2 * 1024 * 1024,  # 2 MB
    backup_count: int = 10,
) -> APIQueryLogger:
    """
    Get or create a singleton APIQueryLogger instance.
    """
    global _api_query_logger_instance

    async with _api_query_logger_lock:
        if _api_query_logger_instance is None:
            _api_query_logger_instance = APIQueryLogger(
                log_file_path=log_file_path,
                max_file_size_bytes=max_file_size_bytes,
                backup_count=backup_count,
            )

        return _api_query_logger_instance