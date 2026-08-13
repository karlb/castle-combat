import pygame
import pytest

from castle_combat import menu
from castle_combat.state import MainState, State
from castle_combat.widget import LineEdit


def keydown(char, key):
    """A KEYDOWN carrying the fields pygame-ce actually puts on one"""
    return pygame.event.Event(
        pygame.KEYDOWN,
        {"unicode": char, "key": key, "mod": 0, "scancode": 0, "window": None},
    )


@pytest.fixture
def server_field():
    """The Server field of the join screen, opened for editing"""
    MainState()
    join_screen = menu.JoinGameState()
    field = [w for w in join_screen.widgets if isinstance(w, LineEdit)][0]
    field.value = "host"
    # what Widget.handle_event does when the field is clicked
    field.on_click()
    return field


def test_typing_appends_to_the_value(server_field):
    """Used to read event.str, which pygame-ce events do not have

    The AttributeError escaped State.on_event, which catches only IgnoreEvent,
    and killed the reactor callback that reschedules the main loop, so the game
    froze on the first printable key. Backspace and Return are handled earlier
    and kept working, which is what made it look like the field was editable.
    """
    State.on_event(keydown("s", pygame.K_s))

    assert server_field.value == "hosts"


def test_backspace_removes_the_last_character(server_field):
    State.on_event(keydown("\x08", pygame.K_BACKSPACE))

    assert server_field.value == "hos"


def test_unprintable_keys_are_ignored(server_field):
    """Arrow keys report an empty string, control characters a real one"""
    State.on_event(keydown("", pygame.K_LEFT))
    State.on_event(keydown("\t", pygame.K_TAB))

    assert server_field.value == "host"


@pytest.mark.parametrize("key", [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE])
def test_the_confirming_keys_leave_the_edit_state(server_field, key):
    """Both Enters, so the keypad one is not left typing nothing

    "\\r".isprintable() is False, so once the printable branch took over from
    the old event.str, keypad Enter fell through every branch silently.
    """
    editing = State.stack[-1]

    State.on_event(keydown("\r", key))

    assert State.stack[-1] is not editing
    assert server_field.value == "host"
