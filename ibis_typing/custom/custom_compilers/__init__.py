"""Implements ibis.Backend compiler support for custom_operations.py."""

from __future__ import annotations

from . import core, duckdb, sqlite, trino

__all__ = ["core", "duckdb", "register_operations", "sqlite", "trino"]


def register_operations():
    # Note: Operations are registered simply by importing the backend modules.
    # This provides an explicit function to trigger the import.
    ...
