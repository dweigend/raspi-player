"""Offline card-creation entry point; implementation lives in focused modules."""


def main() -> None:
    """Start the native GUI or an explicitly requested preparation command."""
    from raspi_player.cli import main as run

    run()
