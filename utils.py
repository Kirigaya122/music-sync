import re
import unicodedata

def normalize_text(value: str) -> str:
    """Normalize text for basic cross-source matching."""
    value = unicodedata.normalize("NFKC", value)
    value = value.casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())