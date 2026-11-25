"""
Synchronous tool helpers (kept for reference).
The live voice pipeline uses the async versions in pipeline/bot.py.
"""
from services.appointments import book, cancel

__all__ = ["book", "cancel"]
