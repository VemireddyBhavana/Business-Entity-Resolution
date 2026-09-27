import re
import pandas as pd
from rapidfuzz import fuzz

def soundex(name):
    """Generates 4-character Soundex phonetic key for an input string."""
    if not name: return '0000'
    name = re.sub(r'[^A-Z]', '', str(name).upper())
    if not name: return '0000'
    table = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    first = name[0]
    tail = [table.get(ch, '0') for ch in name[1:]]
    compact = []
    prev = table.get(first, '0')
    for code in tail:
        if code != '0' and code != prev:
            compact.append(code)
        prev = code
    return (first + ''.join(compact) + '000')[:4]

def extract_feature_vector(b1, b2):
    """Calculates all 13 similarity and length features between two business entities."""
    n1 = b1.get('clean_business_name', '')
    n2 = b2.get('clean_business_name', '')
    a1 = b1.get('clean_business_address', '')
    a2 = b2.get('clean_business_address', '')
    
    w1 = n1.split()[0] if n1.split() else ''
    w2 = n2.split()[0] if n2.split() else ''
    first_w = 1 if (w1 and w1 == w2) else 0
    
    lw1 = n1.split()[-1] if n1.split() else ''
    lw2 = n2.split()[-1] if n2.split() else ''
    last_w = 1 if (lw1 and lw1 == lw2) else 0
    
    c1, s1 = b1.get('city', ''), b1.get('state', '')
    c2, s2 = b2.get('city', ''), b2.get('state', '')
    city_m = int(c1.lower() == c2.lower()) if (c1 and c2) else 0
    state_m = int(s1.lower() == s2.lower()) if (s1 and s2) else 0
    country_m = 1 if b1.get('country') == b2.get('country') else 0
    
    return [
        fuzz.ratio(n1, n2),
        fuzz.ratio(a1, a2),
        country_m,
        abs(len(n1) - len(n2)),
        abs(len(a1) - len(a2)),
        first_w,
        last_w,
        len(set(n1.split()).intersection(set(n2.split()))),
        fuzz.token_sort_ratio(n1, n2),
        fuzz.token_set_ratio(n1, n2),
        fuzz.partial_ratio(n1, n2),
        city_m,
        state_m
    ]

feature_names = [
    'name_similarity', 'address_similarity', 'country_match',
    'name_length_difference', 'address_length_difference',
    'first_word_match', 'last_word_match', 'common_word_count',
    'token_sort_ratio', 'token_set_ratio', 'partial_ratio',
    'city_match', 'state_match'
]
