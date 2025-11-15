import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import json
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from typing import Dict, Tuple, Optional, List
from rapidfuzz import process, fuzz
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Budget Tracker",
    page_icon="💰",
    layout="wide"
)

# Import your helper functions from main.py
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
        sub = row.get("sub-category") if "sub-category" in row else row.get("sub_category")
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

def get_available_folders():
    """Get list of available folders in the current directory"""
    current_dir = os.getcwd()
    folders = [d for d in os.listdir(current_dir) 
              if os.path.isdir(os.path.join(current_dir, d)) 
              and not d.startswith('.')]
    return sorted(folders)

def get_available_files(folder_name):
    """Get list of available CSV files from specified directory"""
    if not folder_name:
        return []
        
    absolute_path = os.path.abspath(folder_name)
    
    if not os.path.exists(absolute_path):
        return []
    
    csv_files = [f for f in os.listdir(absolute_path) if f.lower().endswith(".csv")]
    return sorted(csv_files)

@st.cache_data
def load_and_process_data(selected_files, folder_name):
    """Load and process budget data with caching"""
    try:
        # Load source files
        absolute_path = os.path.abspath(folder_name)
        
        if not os.path.exists(absolute_path):
            return None, None, f"Selected folder not found: {absolute_path}"
        
        if not selected_files:
            return None, None, "No files selected for processing"
        
        # Read and combine selected source files
        df_list = []
        for filename in selected_files:
            file_path = os.path.join(absolute_path, filename)
            if not os.path.exists(file_path):
                return None, None, f"Selected file not found: {filename}"
            
            temp_df = standardize_cols(pd.read_csv(file_path))
            temp_df["source_file"] = filename
            required_src = {"date", "description", "amount", "card"}
            if not required_src.issubset(set(temp_df.columns)):
                return None, None, f"Source file {filename} missing required columns: {required_src - set(temp_df.columns)}"
            df_list.append(temp_df)
        
        src = pd.concat(df_list, ignore_index=True)
        
        # Load reference file
        reference_file = "references.csv"
        if not os.path.exists(reference_file):
            return None, None, f"Reference file not found: {reference_file}"
        
        ref = standardize_cols(pd.read_csv(reference_file))
        required_ref = {"description", "category", "sub-category"}
        if not required_ref.issubset(set(ref.columns)):
            missing = required_ref - set(ref.columns)
            return None, None, f"Reference file missing required columns: {missing}"
        
        # Process data
        desc_to_pair = build_description_lookup(ref)
        all_choices = list(desc_to_pair.keys())
        suggestions = []
        
        for _, row in src.iterrows():
            nd = normalize(row["description"])
            cat = None
            sub = None
            match_type = "none"
            match_desc = None
            match_score = 0.0
            
            # Exact match
            if nd in desc_to_pair and all(v is not None for v in desc_to_pair[nd]):
                cat, sub = desc_to_pair[nd]
                match_type = "exact"
                match_desc = nd
                match_score = 100.0
            else:
                # Fuzzy match
                best, score = fuzzy_best_match(nd, all_choices, threshold=90)
                if best is not None and score >= 90 and all(v is not None for v in desc_to_pair.get(best, (None, None))):
                    cat, sub = desc_to_pair[best]
                    match_type = "fuzzy"
                    match_desc = best
                    match_score = score
            
            suggestion = {
                "date": row.get("date"),
                "description": row.get("description"),
                "amount": row.get("amount"),
                "card": row.get("card"),
                "source_file": row.get("source_file"),
                "category": cat,
                "sub-category": sub,
                "match_type": match_type,
                "matched_description_norm": match_desc,
                "match_score": round(match_score, 1),
                "needs_review": match_type != "exact",
                "reason": "exact" if match_type == "exact" else ("fuzzy_suggest" if match_type == "fuzzy" else "no_match"),
            }
            suggestions.append(suggestion)
        
        suggest_df = pd.DataFrame(suggestions)
        return src, suggest_df, None
        
    except Exception as e:
        return None, None, str(e)

def update_references_file(description, category, subcategory):
    """Update both references.csv and categories.json files with new categorization"""
    
    # 1. Update references.csv
    ref_file = "references.csv"
    
    # Read existing references
    if os.path.exists(ref_file):
        ref_df = pd.read_csv(ref_file)
    else:
        # Create new references file if it doesn't exist
        ref_df = pd.DataFrame(columns=['description', 'category', 'sub-category'])
    
    # Standardize columns
    ref_df = standardize_cols(ref_df)
    
    # Check if description already exists
    existing_row = ref_df[ref_df['description'].str.lower().str.strip() == description.lower().strip()]
    
    if len(existing_row) > 0:
        # Update existing row
        ref_df.loc[existing_row.index[0], 'category'] = category
        ref_df.loc[existing_row.index[0], 'sub-category'] = subcategory
    else:
        # Add new row
        new_row = pd.DataFrame({
            'description': [description],
            'category': [category],
            'sub-category': [subcategory]
        })
        ref_df = pd.concat([ref_df, new_row], ignore_index=True)
    
    # Save updated references
    ref_df.to_csv(ref_file, index=False)
    
    # 2. Update categories.json if new category or subcategory
    categories_file = "categories.json"
    
    # Load existing categories
    if os.path.exists(categories_file):
        with open(categories_file, 'r') as f:
            categories_data = json.load(f)
    else:
        categories_data = {"categories": []}
    
    # Find if category exists
    category_found = False
    for cat_info in categories_data['categories']:
        if cat_info.get('category') == category:
            category_found = True
            # Add subcategory if it doesn't exist
            if subcategory not in cat_info.get('subcategories', []):
                cat_info['subcategories'].append(subcategory)
                cat_info['subcategories'] = sorted(cat_info['subcategories'])
            break
    
    # Add new category if not found
    if not category_found:
        categories_data['categories'].append({
            "category": category,
            "subcategories": [subcategory]
        })
        # Sort categories alphabetically
        categories_data['categories'] = sorted(categories_data['categories'], key=lambda x: x['category'])
    
    # Save updated categories
    with open(categories_file, 'w') as f:
        json.dump(categories_data, f, indent=4)
    
    return True

def create_expense_charts(suggest_df):
    """Create expense breakdown charts"""
    reviewed_df = suggest_df[suggest_df["needs_review"] == False]
    
    if len(reviewed_df) == 0:
        return None
    
    # Compute totals
    cat_totals = reviewed_df.groupby("category")["amount"].sum().sort_values(ascending=False)
    subcat_totals = reviewed_df.groupby(["category", "sub-category"])["amount"].sum()
    
    # Create figure
    fig = plt.figure(figsize=(12, 10))
    gs = fig.add_gridspec(3, 2)
    
    # Main overall pie chart
    ax_main = fig.add_subplot(gs[0, :], aspect='equal')
    wedges, texts, autotexts = ax_main.pie(
        cat_totals,
        labels=cat_totals.index,
        autopct=lambda p: f'{p:.1f}%\n(${p*cat_totals.sum()/100:.2f})',
        startangle=90,
        wedgeprops=dict(width=0.5)
    )
    ax_main.set_title("Overall Expenses by Category", fontsize=14, fontweight='bold')
    
    # Subcategory pies (top 4 categories)
    top_categories = cat_totals.head(4).index.tolist()
    for i, cat in enumerate(top_categories):
        row = 1 + i // 2
        col = i % 2
        ax = fig.add_subplot(gs[row, col], aspect='equal')
        subs = subcat_totals.loc[cat].sort_values(ascending=False)
        
        wedges, texts, autotexts = ax.pie(
            subs,
            labels=subs.index,
            autopct=lambda p: f'{p:.1f}%\n(${p*subs.sum()/100:.2f})',
            startangle=90,
            wedgeprops=dict(width=0.5)
        )
        ax.set_title(f"{cat}\nTotal ${subs.sum():.2f}", fontsize=12, fontweight='bold')
    
    plt.suptitle("Expense Breakdown by Category and Sub-Category", fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    return fig

# Main app
st.title("💰 Personal Budget Tracker")

# Folder Selection Section
st.sidebar.title("📁 Folder Selection")
available_folders = get_available_folders()

if not available_folders:
    st.sidebar.error("No folders found in the current directory")
    st.error("No folders found!")
    st.info("Please create folders with CSV files in your BudgetApp directory")
    st.stop()

# Folder selection dropdown
selected_folder = st.sidebar.selectbox(
    "Choose folder containing CSV files:",
    options=available_folders,
    index=available_folders.index("Source files") if "Source files" in available_folders else 0,
    help="Select the folder that contains your transaction CSV files"
)

# File Selection Section
st.sidebar.title("📂 File Selection")
available_files = get_available_files(selected_folder)

if not available_files:
    st.sidebar.error(f"No CSV files found in '{selected_folder}' folder")
    st.error(f"No CSV files found in '{selected_folder}' folder!")
    st.info(f"Please add CSV files to the '{selected_folder}' folder")
    st.stop()

# File selection options
st.sidebar.write("**File Processing Options:**")

# Radio button for selection mode
selection_mode = st.sidebar.radio(
    "Choose selection mode:",
    ["Process All Files", "Select Specific Files"],
    index=0,  # Default to "Process All Files"
    help="Choose whether to process all files or select specific ones"
)

if selection_mode == "Process All Files":
    selected_files = available_files
    st.sidebar.success(f"Processing all {len(available_files)} files from '{selected_folder}'")
    with st.sidebar.expander("View all files"):
        for file in available_files:
            st.write(f"• {file}")
else:
    # File selection with multiselect
    st.sidebar.write("**Select specific files to process:**")
    selected_files = st.sidebar.multiselect(
        "Available CSV files:",
        options=available_files,
        default=[],  # Start with none selected for manual selection
        help=f"Choose which CSV files from '{selected_folder}' directory to analyze"
    )
    
    # Add select all / deselect all buttons for manual mode
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Select All", key="select_all"):
            st.session_state.multiselect_key = available_files
    with col2:
        if st.button("Clear All", key="clear_all"):
            st.session_state.multiselect_key = []

# Show selected files info
if selected_files:
    if selection_mode == "Process All Files":
        st.sidebar.info(f"✅ All {len(selected_files)} files will be processed")
    else:
        st.sidebar.success(f"Selected {len(selected_files)} file(s)")
        with st.sidebar.expander("View selected files"):
            for file in selected_files:
                st.write(f"• {file}")
else:
    if selection_mode == "Select Specific Files":
        st.sidebar.warning("No files selected")
    else:
        st.sidebar.error("No files found to process")

# Navigation
st.sidebar.markdown("---")
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Dashboard", "Transaction Analysis", "Data Review", "Analytics"])

# Load data only if files are selected
if not selected_files:
    st.warning("⚠️ Please select at least one file from the sidebar to proceed.")
    st.stop()

# Load data with selected files
src_df, suggest_df, error = load_and_process_data(selected_files, selected_folder)

if error:
    st.error(f"Error loading data: {error}")
    st.info("Please ensure you have:")
    st.info("1. Selected valid CSV files with columns: date, description, amount, card")
    st.info("2. A 'references.csv' file with: description, category, sub-category")
    st.stop()

if page == "Dashboard":
    st.header("📊 Dashboard")
    
    if suggest_df is not None:
        # Show file processing info
        st.info(f"Processing {len(selected_files)} selected file(s) from '{selected_folder}' folder: {', '.join(selected_files)}")
        
        # Calculate metrics
        total_transactions = len(suggest_df)
        total_amount = suggest_df["amount"].sum()
        reviewed_count = len(suggest_df[suggest_df["needs_review"] == False])
        needs_review_count = len(suggest_df[suggest_df["needs_review"] == True])
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transactions", total_transactions)
        with col2:
            st.metric("Total Amount", f"${total_amount:,.2f}")
        with col3:
            st.metric("Auto-Categorized", reviewed_count)
        with col4:
            st.metric("Need Review", needs_review_count)
        
        # Progress bar
        if total_transactions > 0:
            progress = reviewed_count / total_transactions
            st.progress(progress, text=f"Categorization Progress: {progress:.1%}")
        
        # File breakdown
        st.subheader("📁 File Breakdown")
        file_summary = suggest_df.groupby("source_file").agg({
            "amount": ["sum", "count"]
        }).round(2)
        file_summary.columns = ["Total Amount", "Transaction Count"]
        st.dataframe(file_summary, use_container_width=True)

elif page == "Transaction Analysis":
    st.header("💳 Transaction Analysis")
    
    if suggest_df is not None:
        # Show categorized transactions
        reviewed_df = suggest_df[suggest_df["needs_review"] == False]
        
        if len(reviewed_df) > 0:
            st.subheader("Categorized Transactions")
            display_df = reviewed_df[["date", "description", "amount", "category", "sub-category", "match_type", "source_file"]].copy()
            st.dataframe(display_df, use_container_width=True)
            
            # Category breakdown
            st.subheader("Category Breakdown")
            cat_summary = reviewed_df.groupby("category")["amount"].agg(["sum", "count"]).round(2)
            cat_summary.columns = ["Total Amount", "Transaction Count"]
            cat_summary = cat_summary.sort_values("Total Amount", ascending=False)
            st.dataframe(cat_summary, use_container_width=True)
        else:
            st.info("No automatically categorized transactions found.")

elif page == "Data Review":
    st.header("🔍 Data Review")
    
    if suggest_df is not None:
        needs_review_df = suggest_df[suggest_df["needs_review"] == True]
        
        if len(needs_review_df) > 0:
            st.subheader("Transactions Needing Review")
            st.write(f"Found {len(needs_review_df)} transactions that need manual review:")
            
            # Initialize session state for tracking updates
            if 'updated_transactions' not in st.session_state:
                st.session_state.updated_transactions = {}
            if 'show_success' not in st.session_state:
                st.session_state.show_success = False
            
            # Get existing categories from categories.json
            categories_file = "categories.json"
            existing_categories = []
            existing_subcategories = {}
            
            if os.path.exists(categories_file):
                with open(categories_file, 'r') as f:
                    categories_data = json.load(f)
                
                for cat_info in categories_data.get('categories', []):
                    category = cat_info.get('category')
                    subcategories = cat_info.get('subcategories', [])
                    if category:
                        existing_categories.append(category)
                        existing_subcategories[category] = subcategories
                
                existing_categories = sorted(existing_categories)
            
            # Show transaction editor as table
            st.markdown("### Edit Transactions")
            
            # Create editable table
            if len(needs_review_df) > 0:
                # Display transactions in a table with edit controls
                for i, (idx, row) in enumerate(needs_review_df.iterrows()):
                    st.markdown(f"#### Transaction {i+1}")
                    
                    # Create columns for the table-like layout
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.markdown("**Transaction Details:**")
                        st.write(f"📅 **Date:** {row['date']}")
                        st.write(f"💳 **Description:** {row['description']}")
                        st.write(f"💰 **Amount:** ${row['amount']:.2f}")
                        st.write(f"📁 **File:** {row['source_file']}")
                        st.write(f"🔍 **Reason:** {row['reason']}")
                        if row['match_score'] > 0:
                            st.write(f"📊 **Match Score:** {row['match_score']}%")
                    
                    with col2:
                        st.markdown("**Category:**")
                        # Category selection/input
                        category_options = ["Select Category", "Add New Category"] + existing_categories
                        selected_cat_option = st.selectbox(
                            "Choose Category",
                            options=category_options,
                            key=f"cat_select_{idx}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_cat_option == "Add New Category":
                            new_category = st.text_input(
                                "Enter new category:",
                                key=f"new_cat_{idx}",
                                placeholder="e.g., Food, Transportation"
                            )
                            final_category = new_category if new_category else None
                        elif selected_cat_option != "Select Category":
                            final_category = selected_cat_option
                        else:
                            final_category = None
                    
                    with col3:
                        st.markdown("**Sub-Category:**")
                        # Sub-category selection/input
                        if final_category and final_category in existing_subcategories:
                            subcat_options = ["Select Sub-Category", "Add New Sub-Category"] + existing_subcategories[final_category]
                        else:
                            subcat_options = ["Select Sub-Category", "Add New Sub-Category"]
                        
                        selected_subcat_option = st.selectbox(
                            "Choose Sub-Category",
                            options=subcat_options,
                            key=f"subcat_select_{idx}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_subcat_option == "Add New Sub-Category":
                            new_subcategory = st.text_input(
                                "Enter new sub-category:",
                                key=f"new_subcat_{idx}",
                                placeholder="e.g., Groceries, Gas"
                            )
                            final_subcategory = new_subcategory if new_subcategory else None
                        elif selected_subcat_option != "Select Sub-Category":
                            final_subcategory = selected_subcat_option
                        else:
                            final_subcategory = None
                    
                    with col4:
                        st.markdown("**Action:**")
                        # Update button for each transaction
                        if st.button("💾 Update", key=f"update_{idx}", help="Save categorization"):
                            if final_category and final_subcategory:
                                # Update the transaction in session state
                                st.session_state.updated_transactions[idx] = {
                                    'category': final_category,
                                    'sub-category': final_subcategory,
                                    'description': row['description']
                                }
                                
                                # Update references.csv
                                update_references_file(row['description'], final_category, final_subcategory)
                                
                                st.success(f"✅ {final_category} → {final_subcategory}")
                                st.session_state.show_success = True
                            else:
                                st.error("❌ Select both fields")
                    
                    # Add a separator between transactions
                    st.divider()
            
            # Show updated transactions summary
            if st.session_state.updated_transactions:
                st.markdown("### 📊 Recently Updated Transactions")
                updated_df = pd.DataFrame([
                    {
                        'Description': data['description'][:50] + '...' if len(data['description']) > 50 else data['description'],
                        'Category': data['category'],
                        'Sub-Category': data['sub-category']
                    }
                    for data in st.session_state.updated_transactions.values()
                ])
                st.dataframe(updated_df, use_container_width=True)
                
                if st.button("🔄 Refresh Analysis", type="primary"):
                    # Clear cache to reload data with new categorizations
                    st.cache_data.clear()
                    st.session_state.updated_transactions = {}
                    st.rerun()
            
            # Show unresolved transactions
            unresolved_count = len(needs_review_df) - len(st.session_state.updated_transactions)
            if unresolved_count > 0:
                st.info(f"📋 {unresolved_count} transactions still need review")
            
            # Show reasons breakdown
            st.subheader("Review Reasons Breakdown")
            reason_counts = needs_review_df["reason"].value_counts()
            st.bar_chart(reason_counts)
            
        else:
            st.success("🎉 All transactions have been successfully categorized!")
            st.balloons()

elif page == "Analytics":
    st.header("📈 Budget Analytics")
    
    if suggest_df is not None:
        reviewed_df = suggest_df[suggest_df["needs_review"] == False]
        
        if len(reviewed_df) > 0:
            # Create and display charts
            fig = create_expense_charts(suggest_df)
            if fig:
                st.pyplot(fig)
            
            # Additional analytics
            st.subheader("Spending Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Top 5 Categories by Amount:**")
                cat_totals = reviewed_df.groupby("category")["amount"].sum().sort_values(ascending=False).head()
                for cat, amount in cat_totals.items():
                    st.write(f"• {cat}: ${amount:,.2f}")
            
            with col2:
                st.write("**Top 5 Most Frequent Categories:**")
                cat_counts = reviewed_df["category"].value_counts().head()
                for cat, count in cat_counts.items():
                    st.write(f"• {cat}: {count} transactions")
        else:
            st.info("No categorized data available for analytics. Please review transactions first.")

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.info("💡 **Tips:**\n- Select different folders to analyze different datasets\n- Use 'Process All Files' for quick analysis\n- Check Data Review for unmatched transactions\n- Use Analytics to see spending patterns")