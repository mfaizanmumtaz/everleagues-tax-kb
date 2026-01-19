"""Configuration package for the application."""

# Import settings to make them available at package level
from .settings import settings, Settings, get_settings

__all__ = ["settings", "Settings", "get_settings"]
