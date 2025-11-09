import pandas as pd
import csv
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

def load_patterns(patterns_file: str) -> Dict[str, List[str]]:
    """Load patterns from CSV file into a dict of card_name -> column headers."""
    patterns = {}
    with open(patterns_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:  # Skip empty rows
                card_name = row[0]
                # Store the column pattern (excluding card name)
                patterns[card_name] = [col.strip() for col in row[1:] if col.strip()]
    return patterns

def find_matching_pattern(file_content: List[str], patterns: Dict[str, List[str]]) -> Tuple[Optional[str], Optional[List[str]], int]:
    """
    Find which pattern matches the file content and return:
    - card_name: name of the matching card pattern
    - headers: the matching column headers
    - start_idx: line number where the headers were found
    """
    for card_name, pattern_headers in patterns.items():
        # Look through each line in the file
        for idx, line in enumerate(file_content):
            # Split the line into columns
            row = [col.strip() for col in line.split(',')]
            # Check if this line matches our pattern headers
            if all(header in row for header in pattern_headers):
                return card_name, pattern_headers, idx
    return None, None, -1

def parse_date(date_str: str) -> str:
    """Convert various date formats to YYYY-MM-DD."""
    try:
        # Handle common date formats
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        raise ValueError(f"Could not parse date: {date_str}")
    except:
        return date_str  # Return original if parsing fails

def normalize_amount(amount_str: str) -> float:
    """Convert amount string to float, handling credits/debits."""
    try:
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[^\d.-]', '', amount_str)
        # Convert to float
        amount = float(cleaned)
        # Some statements use negative for debits, others use separate debit/credit columns
        # We'll standardize to negative=debit, positive=credit
        return amount
    except:
        return 0.0

def parse_statement_file(input_file: str, patterns_file: str) -> pd.DataFrame:
    """
    Parse a credit card statement CSV file using patterns from patterns_file.
    Returns a DataFrame with standardized date, description, and amount columns.
    
    Args:
        input_file: Path to the statement CSV file
        patterns_file: Path to the patterns CSV file containing header patterns
    
    Returns:
        DataFrame with columns: date, description, amount
    """
    # Load patterns
    patterns = load_patterns(patterns_file)
    
    # Read the entire input file
    with open(input_file, 'r') as f:
        file_content = f.readlines()
    
    # Find matching pattern and where data starts
    card_name, headers, start_idx = find_matching_pattern(file_content, patterns)
    
    if not card_name or not headers:
        raise ValueError(f"No matching pattern found for {input_file}")
    
    # Find the indices for date, description, and amount based on card pattern
    # Date column: first column that contains "date"
    date_col = next((i for i, h in enumerate(headers) if 'date' in h.lower()), None)
    
    # Description column: look for "description" or "payee"
    desc_col = next((i for i, h in enumerate(headers) if any(term in h.lower() for term in ['description', 'payee'])), None)
    
    # Set up amount columns based on card type
    if card_name.lower() == 'pnc credit':
        # Find Withdrawals and Deposits columns
        debit_col = next((i for i, h in enumerate(headers) if h.lower() == 'withdrawals'), None)
        credit_col = next((i for i, h in enumerate(headers) if h.lower() == 'deposits'), None)
        if debit_col is None or credit_col is None:
            raise ValueError(f"Could not find Withdrawals/Deposits columns for PNC Credit. Headers: {headers}")
        amount_cols = [(debit_col, credit_col, 'dc')]  # dc = debit/credit
    elif card_name.lower() == 'citi credit':
        # Find Debit and Credit columns
        debit_col = next((i for i, h in enumerate(headers) if h.lower() == 'debit'), None)
        credit_col = next((i for i, h in enumerate(headers) if h.lower() == 'credit'), None)
        if debit_col is None or credit_col is None:
            raise ValueError(f"Could not find Debit/Credit columns for Citi Credit. Headers: {headers}")
        amount_cols = [(debit_col, credit_col, 'dc')]  # dc = debit/credit
    else:
        # For all other cards, look for single amount column
        amount_col = next((i for i, h in enumerate(headers) if h.lower() == 'amount'), None)
        if amount_col is None:
            raise ValueError(f"Could not find Amount column for {card_name}. Headers: {headers}")
        amount_cols = [(amount_col, None, 'single')]
    
    if date_col is None or desc_col is None:
        raise ValueError(f"Could not find required date/description columns for {card_name}. Headers: {headers}")
    
    # Initialize lists for our data
    dates = []
    descriptions = []
    amounts = []
    cards = []  # New list for card names

    # Process each line after the headers
    for line in file_content[start_idx + 1:]:
        row = [col.strip() for col in line.split(',')]
        if len(row) >= len(headers) and any(row):  # Skip empty lines
            # Get date
            if len(row) > date_col and row[date_col]:
                date = parse_date(row[date_col])
                
                # Get description
                description = row[desc_col] if len(row) > desc_col else ''
                
                # Handle amount based on card type
                amount = 0.0
                for col1, col2, amt_type in amount_cols:
                    if amt_type == 'dc':  # Debit - Credit
                        debit = normalize_amount(row[col1]) if len(row) > col1 and row[col1] else 0.0
                        credit = normalize_amount(row[col2]) if len(row) > col2 and row[col2] else 0.0
                        amount = debit - credit
                    else:  # Single amount column
                        if len(row) > col1 and row[col1]:
                            amount = normalize_amount(row[col1])
                
                # Only add if we have valid data
                if date and description and amount != 0.0:
                    dates.append(date)
                    descriptions.append(description)
                    amounts.append(amount)
                    cards.append(card_name)  
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'description': descriptions,
        'amount': amounts,
        'card': cards
    })
    
    # Sort by date
    df = df.sort_values('date', ascending=False)
    
    return df

# Example usage
if __name__ == "__main__":
    # Example usage of the function
    input_file = "Example.csv"
    patterns_file = "Patterns.csv"
    
    try:
        df = parse_statement_file(input_file, patterns_file)
        print("\nExtracted transactions:")
        print(df)
        
        # Optionally save to CSV
        output_file = "parsed_transactions.csv"
        df.to_csv(output_file, index=False)
        print(f"\nSaved to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")