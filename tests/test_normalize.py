import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from normalize import normalize  # noqa: E402


def test_case_and_capital_open_vowels():
    assert normalize("Ɔbebue") == "ɔbebue"
    assert normalize("Ɛno akyi no") == "ɛno akyi no"


def test_tone_and_accent_marks_removed():
    assert normalize("Woadi Ńkɔmmɔ mprɛnsa") == "woadi nkɔmmɔ mprɛnsa"
    assert normalize("àkɔ́") == "akɔ"


def test_punctuation_removed_but_elision_apostrophe_kept():
    assert normalize("Ɔbebue n'ani ɔkyena.") == "ɔbebue n'ani ɔkyena"
    assert normalize("Hyɛ n’anim tee!") == "hyɛ n'anim tee"
    assert normalize("'Daabi', ɔkaa sɛ") == "daabi ɔkaa sɛ"


def test_numbers_and_code_switching_untouched():
    assert normalize("Mɛtɔ credit 5 cedis") == "mɛtɔ credit 5 cedis"


def test_greek_epsilon_lookalike():
    assert normalize("yε") == "yɛ"


def test_fold_vowels():
    assert normalize("Mɛtɔ credit", fold_vowels=True) == "meto credit"


def test_whitespace_and_empty():
    assert normalize("  ne   yere \n") == "ne yere"
    assert normalize("") == ""
    assert normalize(None) == ""
