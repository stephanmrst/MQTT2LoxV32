"""Application factory placeholder for the v32 migration.

The active entry point still uses app/main.py and app/engine/port.py.
"""


def create_app():
    """Create the current legacy-backed Flask app without changing startup behavior."""
    from .engine.port import create_legacy_app

    return create_legacy_app()
