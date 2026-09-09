"""Verify the startup checkpoint gates VLC without requiring GTK on the host.

The display itself still requires Pi hardware acceptance; these tests cover the
mapped-window delay and fail-closed behavior before the service's ExecStart.
"""

from unittest.mock import Mock

import pytest

from raspi_player.payload.startup import DISPLAY_SECONDS, StartupScreen


def test_no_vlc_release_before_window_is_mapped() -> None:
    gtk, glib = Mock(), Mock()
    screen = StartupScreen(gtk, glib)
    with pytest.raises(RuntimeError, match="before the visible checkpoint"):
        screen.run()
    glib.timeout_add_seconds.assert_not_called()
    assert not screen.completed


def test_mapping_starts_one_delay_and_does_not_release_vlc() -> None:
    gtk, glib = Mock(), Mock()
    screen = StartupScreen(gtk, glib)
    screen.on_map(None, None)
    screen.on_map(None, None)
    glib.timeout_add_seconds.assert_called_once_with(DISPLAY_SECONDS, screen.finish)
    assert not screen.completed


def test_completed_display_delay_allows_player_start() -> None:
    gtk, glib = Mock(), Mock()
    screen = StartupScreen(gtk, glib)
    gtk.main.side_effect = lambda: (screen.on_map(None, None), screen.finish())
    screen.run()
    assert screen.completed
    gtk.main_quit.assert_called_once()
