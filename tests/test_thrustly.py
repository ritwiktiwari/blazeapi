"""Tests for thrustly."""

from typer.testing import CliRunner

from thrustly import __version__


def test_version() -> None:
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)
