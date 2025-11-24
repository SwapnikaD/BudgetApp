from rapidfuzz import process, fuzz
import os
import pandas as pd
from typing import Dict, Tuple, Optional, List
from collections import Counter, defaultdict
import re

def standardize_cols(df: pd.DataFrame) -> pd.DataFrame:
    lower_map = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=lower_map)
    return df

def normalize(text: str) -> str:
    if not isinstance(text, str):
        text = "" if pd.isna(text) else str(text)
    t = text.strip().lower()
    t = re.compile(r"[^\w\s]").sub(" ", t)
    t = re.compile(r"\s+").sub(" ", t)
    return t.strip()

def most_common_pair(pairs: List[Tuple[str, str]]) -> Tuple[Optional[str], Optional[str]]:
    if not pairs:
        return None, None
    counter = Counter(pairs)
    (cat, subcat), _ = counter.most_common(1)[0]
    return cat, subcat

def build_description_lookup(dest_df: pd.DataFrame) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    pairs_by_desc: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for _, row in dest_df.iterrows():
        nd = normalize(row.get("description", ""))
        cat = row.get("category")
        sub = row.get("subcategory") if "subcategory" in row else row.get("sub_category")
        if pd.notna(cat) and pd.notna(sub):
            pairs_by_desc[nd].append((str(cat), str(sub)))
    lookup: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    for nd, pairs in pairs_by_desc.items():
        lookup[nd] = most_common_pair(pairs)
    return lookup

def fuzzy_best_match(query: str, choices: List[str], threshold: int = 90) -> Tuple[Optional[str], float]:
    if not choices:
        return None, 0.0
    match = process.extractOne(query, choices, scorer=fuzz.token_set_ratio)
    if match is None:
        return None, 0.0
    choice, score, _ = match
    return choice, float(score)


def categorize_parsed_data(src: pd.DataFrame, reference_file: str) -> pd.DataFrame:
    """Categorizes parsed transaction data based on a reference CSV file.

    Args:
        parsed_data (pd.DataFrame): DataFrame containing parsed transactions with at least
                                    'description' column.
        reference_file (str): Path to the reference CSV file containing at least 'description', 'category' and 'subcategory'.

    Returns:
        pd.DataFrame: The input DataFrame with added 'category', 'subcategory', 'match_type' and 'match_score' columns.
    """
  # Load reference file 
    if not os.path.exists(reference_file):
        return None, None, f"Reference file not found: {reference_file}"
    ref = standardize_cols(pd.read_csv(reference_file))
    required_ref = {"description", "category", "subcategory"}
    if not required_ref.issubset(set(ref.columns)):
        missing = required_ref - set(ref.columns)
        return None, None, f"Reference file missing required columns: {missing}"

    # Process data
    src = standardize_cols(src)
    desc_to_pair = build_description_lookup(ref)
    all_choices = list(desc_to_pair.keys())
    suggestions = []
    for _, row in src.iterrows():
        nd = normalize(row["description"])
        cat = None
        sub = None
        match_type = "none"
        match_score = 0.0
        
        # Exact match
        if nd in desc_to_pair and all(v is not None for v in desc_to_pair[nd]):
            cat, sub = desc_to_pair[nd]
            match_type = "exact"
            match_score = 100.0
        else:
            # Fuzzy match
            best, score = fuzzy_best_match(nd, all_choices, threshold=50)
            if best is not None and score >= 50 and all(v is not None for v in desc_to_pair.get(best, (None, None))):
                cat, sub = desc_to_pair[best]
                match_type = "fuzzy"
                match_score = score
        
        suggestion = {
            "date": row.get("date"),
            "description": row.get("description"),
            "amount": row.get("amount"),
            "card": row.get("card"),
            "category": cat,
            "subcategory": sub,
            "match_type": match_type,
            "match_score": round(match_score, 1)
        }
        suggestions.append(suggestion)

    suggest_df = pd.DataFrame(suggestions)
    return suggest_df