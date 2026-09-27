from lionel_types import settings as store
from lionel_types.settings import Settings


def test_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    original = Settings(sound=False, theme="classic", mode="find")
    store.save(original, path)
    assert store.load(path) == original


def test_missing_or_corrupt_files_fall_back_to_defaults(tmp_path):
    assert store.load(tmp_path / "nope.json") == Settings()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert store.load(bad) == Settings()


def test_unknown_or_invalid_values_are_ignored():
    loaded = Settings.from_dict({"theme": "plaid", "sound": "yes", "voice": False, "extra": 1})
    assert loaded == Settings(voice=False)


def test_cycle_wraps_around():
    settings = Settings()
    for _ in range(3):
        settings.cycle("text_size")
    assert settings.text_size == "big"
