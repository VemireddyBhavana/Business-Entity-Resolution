import re, string
import pandas as pd

def remove_company_suffix(name):
    """Strips standard company legal suffixes (e.g. Pvt Ltd, Inc, LLC)."""
    if not name or pd.isna(name): return ''
    suffixes = [
        "private limited", "pvt ltd", "pvt. ltd.", "limited", "ltd",
        "inc", "llc", "corp", "corporation", "co", "company"
    ]
    name = str(name).lower()
    for s in suffixes:
        name = re.sub(r'\b' + re.escape(s) + r'\b', '', name)
    return " ".join(name.split())

def expand_address_abbreviations(address):
    """Expands common address abbreviations (e.g. Rd -> Road, St -> Street)."""
    if not address or pd.isna(address): return ''
    abbreviations = {
        r'\brd\b': 'road', r'\bst\b': 'street', r'\bave\b': 'avenue',
        r'\bblvd\b': 'boulevard', r'\bdr\b': 'drive', r'\bln\b': 'lane', r'\bhwy\b': 'highway'
    }
    address = str(address).lower()
    for short, full in abbreviations.items():
        address = re.sub(short, full, address)
    return " ".join(address.split())

def remove_punctuation(text):
    """Removes punctuation symbols."""
    if not text or pd.isna(text): return ''
    for char in string.punctuation:
        text = str(text).replace(char, ' ')
    return " ".join(text.split())

def clean_business_name(text):
    """Full normalization pipeline for business names."""
    text = remove_punctuation(text)
    text = remove_company_suffix(text)
    replacements = {r'\bhosp\.?\b': 'hospital', r'\bcentre\b': 'center', r'\bco\.?\b': 'company'}
    for old, new in replacements.items():
        text = re.sub(old, new, text)
    stop_words = {'the', 'and', 'of', 'for', 'at', 'by'}
    words = [w for w in text.split() if w not in stop_words]
    return " ".join(words)

def clean_business_address(text):
    """Full normalization pipeline for addresses."""
    text = str(text).lower()
    text = re.sub(r'\bno\.\s*', '', text)
    text = re.sub(r'\bnumber\s*', '', text)
    text = text.replace('#', '')
    text = expand_address_abbreviations(text)
    text = remove_punctuation(text)
    return " ".join(text.split())

def extract_city_state(address):
    """Parses city and state tokens from an address string."""
    if not address or pd.isna(address): return '', ''
    parts = [p.strip() for p in str(address).split(',') if p.strip()]
    if len(parts) >= 3:
        return parts[-2], parts[-1]
    elif len(parts) == 2:
        return parts[0], parts[1]
    return parts[0] if parts else '', ''
