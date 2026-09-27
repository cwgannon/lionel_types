from lionel_types import keys
from lionel_types.parent import HoldGate, ParentMenu
from lionel_types.settings import Settings


def test_gate_fires_once_after_a_steady_hold():
    gate = HoldGate(seconds=2.0)
    assert not any(gate.update(True, 0.5) for _ in range(3))
    assert gate.update(True, 0.5)
    assert not gate.update(True, 5.0)  # must let go before it fires again
    gate.update(False, 0.1)
    assert not gate.update(True, 1.0)


def test_letting_go_resets_the_gate():
    gate = HoldGate(seconds=2.0)
    gate.update(True, 1.9)
    gate.update(False, 0.01)
    assert gate.progress == 0
    assert not gate.update(True, 1.9)


def test_menu_toggles_and_cycles_settings_and_runs_commands():
    settings = Settings()
    changed, commands = [], []
    menu = ParentMenu(settings, changed.append, commands.append)
    menu.key_down(keys.char_key("1"))
    menu.key_down(keys.char_key("3"))
    menu.key_down(keys.char_key("q"))
    menu.key_down(keys.Key(keys.ENTER))
    assert settings.sound is False
    assert settings.letter_case == "lower"
    assert changed == ["sound", "letter_case"]
    assert commands == ["quit", "close"]


def test_menu_closes_itself_when_left_alone():
    commands = []
    menu = ParentMenu(Settings(), lambda name: None, commands.append)
    menu.update(60)
    assert commands == ["close"]
