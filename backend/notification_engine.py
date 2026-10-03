"""Backward-compatibility shim. Imports NotificationEngine from services package."""
from services.notification_engine import NotificationEngine

__all__ = ["NotificationEngine"]
