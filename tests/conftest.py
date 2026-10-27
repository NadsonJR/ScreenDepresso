import pytest


@pytest.fixture(autouse=True)
def noninteractive_window_cleanup(monkeypatch):
    """Existing GUI tests close windows at cleanup without driving a real app exit.

    Close-flow tests override these methods to exercise each explicit user choice.
    """
    from screendepresso.app import MainWindow
    monkeypatch.setattr(MainWindow, 'ask_close_action', lambda self: 'quit')
    monkeypatch.setattr(MainWindow, '_quit_application', lambda self: None)
