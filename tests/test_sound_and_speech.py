from array import array

from lionel_types.sound import NOTE_COUNT, SOUND_NAMES, pentatonic, step_for_char, synthesize, to_pcm
from lionel_types.speech import clean


def test_every_printable_key_has_a_note_in_range():
    steps = {step_for_char(chr(c)) for c in range(32, 127)}
    assert min(steps) >= 0 and max(steps) < NOTE_COUNT


def test_keyboard_rises_left_to_right_and_bottom_to_top():
    assert step_for_char("z") < step_for_char("m")
    assert step_for_char("z") < step_for_char("a") < step_for_char("q") < step_for_char("1")
    assert step_for_char("!") == step_for_char("1")  # shifted keys sound like their key


def test_pentatonic_starts_at_middle_c_and_doubles_each_octave():
    assert round(pentatonic(0), 2) == 261.63
    assert round(pentatonic(5) / pentatonic(0), 6) == 2


def test_every_sound_synthesizes_to_clean_stereo_pcm():
    for name in SOUND_NAMES:
        samples = synthesize(name, 8000)
        pcm = array("h", to_pcm(samples, 0.5, 2))
        assert len(pcm) == 2 * len(samples)
        assert max(abs(v) for v in pcm) <= 32767 * 0.5 + 1
        assert pcm[0::2] == pcm[1::2]
        assert abs(pcm[-1]) < 200  # faded out: no click at the end


def test_speech_text_cannot_become_a_command_option():
    assert clean("--rate 1000") == "rate 1000"
    assert clean("Find the letter B.") == "Find the letter B."
    assert clean("a;b|c&d") == "a b c d"
