"""Switching sound off has to silence the effects, not just the music"""

from castle_combat import sound


def test_sound_off_silences_the_effects():
    sound.sound_on()
    assert not isinstance(sound.cannon, sound.DummySound)

    sound.sound_off()

    assert isinstance(sound.cannon, sound.DummySound)
    assert isinstance(sound.wall_hit, sound.DummySound)
