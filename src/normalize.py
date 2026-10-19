"""Step 4: Twi text normalisation, applied identically to references and
model outputs before scoring.

Two levels:
    normalize(text)                    -> standard scoring text
    normalize(text, fold_vowels=True)  -> also folds ɛ->e, ɔ->o, to measure
                                          how much error is only the special letters
"""
import re
import unicodedata

# Apostrophes / quote variants that appear in Twi elisions (n'ani, w'akyi).
_APOSTROPHES = "’‘ʼ`´"

# Common look-alike substitutions for the Twi open vowels.
_VOWEL_VARIANTS = {
    "Ɛ": "ɛ",  # Ɛ -> ɛ
    "Ɔ": "ɔ",  # Ɔ -> ɔ
    "ε": "ɛ",  # Greek epsilon ε -> ɛ
}

_FOLD = str.maketrans({"ɛ": "e", "ɔ": "o"})


def normalize(text: str, fold_vowels: bool = False) -> str:
    if not text:
        return ""
    # Decompose, so accents/tone marks become separate combining characters...
    text = unicodedata.normalize("NFD", text)
    for k, v in _VOWEL_VARIANTS.items():
        text = text.replace(k, v)
    text = text.lower()
    # ...then drop them: Twi orthography does not mark tone, and the data
    # uses accents inconsistently (e.g. "Ńkɔmmɔ").
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = unicodedata.normalize("NFC", text)

    for a in _APOSTROPHES:
        text = text.replace(a, "'")
    # Keep apostrophes inside words (n'ani), drop all other punctuation.
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"(?<!\w)'|'(?!\w)", " ", text)
    text = text.replace("_", " ")

    if fold_vowels:
        text = text.translate(_FOLD)
    return re.sub(r"\s+", " ", text).strip()
