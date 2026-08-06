"""
Language detection for the chat assistant: English / Roman Urdu / native
Urdu script.

WHY THIS EXISTS
----------------
The previous implementation only checked for native Urdu Unicode
characters. Anything without Urdu script - including Roman Urdu ("mujhe
dawa chahiye") - fell through to a bare "en" classification, and the
*actual* Roman-Urdu-vs-English distinction was left entirely to the LLM's
own implicit judgment via a system-prompt instruction ("respond in Roman
Urdu if the user used Roman Urdu"). That works well enough in practice
because the model is capable, but it isn't NLP performed by this
codebase - it's undocumented, untestable behavior living inside a prompt
string, and it costs the model a hidden text-classification prompt on
every single call.

This module performs the classification explicitly and deterministically
in code, using a genuine (if lightweight) NLP technique: tokenization +
lexicon-based weighted scoring, in the spirit of a Naive Bayes bag-of-
words classifier. Off-the-shelf language-ID libraries (langdetect,
fastText's lid.176, etc.) are deliberately NOT used here - they are
trained on standardized languages and reliably misclassify Roman Urdu as
Indonesian, Malay, or generic noise, since it isn't one of their trained
classes. A curated domain lexicon is the correct, pragmatic tool for this
specific problem.
"""
import re

# ---------------------------------------------------------------------
# Native Urdu script detection (unchanged from before - this part was
# already correct and unambiguous; Unicode range membership is a hard
# fact, not a classification problem).
# ---------------------------------------------------------------------
_URDU_SCRIPT_PATTERN = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
)

# ---------------------------------------------------------------------
# Roman Urdu lexicon: function words (pronouns, particles, question
# words, common verbs/auxiliaries) plus frequent domain vocabulary for a
# hospital booking assistant. Function words carry the real signal since
# they appear regardless of topic (this mirrors how real language-ID
# systems weight closed-class words over open-class/topic words).
# ---------------------------------------------------------------------
_ROMAN_URDU_FUNCTION_WORDS = {
    "hai", "hain", "hoon", "ho", "tha", "thi", "the", "hoga", "hogi",
    "mein", "main", "mujhe", "mera", "meri", "mere", "hum", "humein",
    "hamara", "hamari", "aap", "aapka", "aapki", "aapke", "tum", "tumhe",
    "wo", "woh", "yeh", "ye", "is", "us", "in", "un",
    "ka", "ki", "ke", "ko", "ne", "se", "par", "tak", "liye",
    "kya", "kyun", "kyu", "kaise", "kab", "kahan", "kaun", "konsa",
    "konsi", "kitna", "kitni", "kitne",
    "aur", "ya", "lekin", "magar", "agar", "phir", "bhi", "sirf",
    "nahi", "nahin", "na", "haan", "han", "ji",
    "kar", "karo", "karain", "karna", "kardo", "karta",
    "karti", "karte", "chahiye", "chahta", "chahti", "chahte",
    "raha", "rahi", "rahe", "sakta", "sakti", "sakte",
    "diya", "dena", "dijiye", "milega", "milegi",
    "aaj", "kal", "abhi", "subah", "shaam", "raat", "din",
    "hafte", "haftay", "waqt", "bajay", "baje", "pooch", "rahay", "houn",
}

_ROMAN_URDU_DOMAIN_WORDS = {
    "dawa", "dawai", "dard", "bimari", "bimar", "ilaj", "tabiyat",
    "theek", "acha", "achi", "bura", "buri", "zaroori",
    "doctor", "appointment",  # shared loanwords - low signal alone, but
                                # still counted; scoring is additive
                                # across the whole sentence so they rarely
                                # decide a classification by themselves.
}

_ROMAN_URDU_LEXICON = _ROMAN_URDU_FUNCTION_WORDS | _ROMAN_URDU_DOMAIN_WORDS

# ---------------------------------------------------------------------
# English function words - same idea, for the other side of the score.
# ---------------------------------------------------------------------
_ENGLISH_FUNCTION_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "am",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his",
    "her", "our", "their", "this", "that", "these", "those",
    "what", "why", "how", "when", "where", "who", "which",
    "and", "or", "but", "if", "then", "also", "only",
    "not", "no", "yes",
    "do", "does", "did", "can", "could", "would", "should", "will",
    "shall", "have", "has", "had", "want", "need", "please",
    "today", "tomorrow", "now", "later", "morning", "evening", "night",
    "day", "week", "time", "at", "on", "in", "for", "to", "with", "of",
}

_TOKEN_PATTERN = re.compile(r"[a-zA-Z']+")


def _tokenize(text: str) -> list:
    """Lowercase word tokenization, stripping punctuation/digits."""
    return _TOKEN_PATTERN.findall(text.lower())


def classify_roman_script(text: str):
    """
    Scores Latin-script text as English vs Roman Urdu.
    Returns (label, confidence) where label is "en" or "roman_ur" and
    confidence is a float in [0, 1] - the fraction of lexicon matches
    belonging to the winning class (0.5 = a tie, resolved to English as
    the safer default).
    """
    tokens = _tokenize(text)
    if not tokens:
        return "en", 0.5

    roman_hits = sum(1 for t in tokens if t in _ROMAN_URDU_LEXICON)
    english_hits = sum(1 for t in tokens if t in _ENGLISH_FUNCTION_WORDS)

    total = roman_hits + english_hits
    if total == 0:
        # No lexicon signal at all (e.g. a lone doctor's name, a bare
        # number) - default to English rather than guess.
        return "en", 0.5

    roman_ratio = roman_hits / total
    if roman_ratio > 0.5:
        return "roman_ur", roman_ratio
    return "en", 1 - roman_ratio


def detect_language(text: str) -> str:
    """
    Returns one of: "ur" (native Urdu script), "roman_ur" (Roman-script
    Urdu), "en" (English). This is the single source of truth for
    language detection used by the chat assistant.
    """
    if not text or not text.strip():
        return "en"

    if _URDU_SCRIPT_PATTERN.search(text):
        return "ur"

    label, _confidence = classify_roman_script(text)
    return label