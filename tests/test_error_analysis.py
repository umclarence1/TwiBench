import sys
from pathlib import Path

import jiwer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from error_analysis import classify, is_hallucination  # noqa: E402


def total_errors(ref, hyp):
    o = jiwer.process_words(ref, hyp)
    return o.substitutions + o.deletions + o.insertions


def test_counts_match_wer_units():
    for ref, hyp in [("melki ba adi ba", "melkiba adiba"), ("mɛtɔ credit 5 cedis", "meto kredit five"),
                     ("ne yere", "ne yere no bi"), ("woadi nkɔmmɔ", "")]:
        assert sum(classify(ref, hyp).values()) == total_errors(ref, hyp)


def test_word_join_is_boundary():
    c = classify("melki ba adi ba", "melkiba adiba")
    assert c["boundary"] == 4 and sum(c.values()) == 4


def test_word_split_is_boundary():
    assert classify("woadi nkɔmmɔ", "woadi nkɔ mmɔ")["boundary"] == 2


def test_vowel_loan_number():
    c = classify("mɛtɔ credit 5 cedis", "meto kredit 6 cedis")
    assert c["vowel"] == 1 and c["loanword"] == 1 and c["number"] == 1


def test_hallucination():
    assert is_hallucination("yosua ba", "ḍḍḍḍḍḍḍḍḍḍḍḍ")
    assert is_hallucination("ne yere", "no no no no no no")
    assert not is_hallucination("ne yere", "ne yɛre")
