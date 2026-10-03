"""Backward-compatibility shim. Imports DatabaseManager from database package."""
from database.manager import DatabaseManager

__all__ = ["DatabaseManager"]
