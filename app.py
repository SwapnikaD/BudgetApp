import streamlit as st
import pandas as pd
import numpy as np
import parse_statement as ps
import re
import os
import json
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from Data_Review import get_item_options
from categorize_parsed_data import categorize_parsed_data
#Initialization
if "suggest_df" not in st.session_state:
    st.session_state["suggest_df"] = None
if "src_df" not in st.session_state:  
    st.session_state["src_df"] = None
patterns_file_path = os.path.join(os.getcwd(),"Patterns.csv")
reference_file = os.path.join(os.getcwd(),"references.csv")
# Helper functions 
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
            
            temp_df = ps.parse_statement_file(file_path, patterns_file_path)
            df_list.append(temp_df)
        src = pd.concat(df_list, ignore_index=True)
        suggest_df = categorize_parsed_data(src, reference_file)
        
        return src, suggest_df, None
        
    except Exception as e:
        return None, None, str(e)
def create_expense_charts(suggest_df):
    """Create expense breakdown charts"""
    reviewed_df = st.session_state["suggest_df"]
    
    if len(reviewed_df) == 0:
        return None
    
    # Compute totals
    cat_totals = reviewed_df.groupby("category")["amount"].sum().sort_values(ascending=False)
    subcat_totals = reviewed_df.groupby(["category", "subcategory"])["amount"].sum()
    
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
@st.dialog("Invald Selection")
def errormsg():
    st.error("❌ Select both fields")
# Main app
# Set page config
st.set_page_config(
    page_title="Budget Tracker",
    page_icon="💰",
    layout="wide"
)

# Navigation
st.sidebar.title("💰 Personal Budget Tracker")
st.sidebar.markdown("---")
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", 
                            ["Process Inputs", "Transaction Analysis", 
                             "Data Review", "Visualization","Master Data"])
st.sidebar.markdown("---")
st.sidebar.info("💡 **Tips:**" \
                "\n- Select different folders to analyze different datasets" \
                "\n- Use 'Process All Files' for quick analysis\n- Check Data Review for unmatched transactions" \
                "\n- Use Visualization to see spending patterns"
                )

if page == "Process Inputs":
    # Folder Selection Section
    st.title("📁 Folder Selection")
    available_folders = get_available_folders()
    if not available_folders:
        st.error("No folders found in the current directory.\n Please create folders with CSV files in your BudgetApp directory")
        st.stop()
    # Folder selection dropdown
    selected_folder = st.selectbox(
        "Choose folder containing CSV files:",
        options=available_folders,
        index=available_folders.index("Source files") if "Source files" in available_folders else 0,
        help="Select the folder that contains your transaction CSV files"
    )# File Selection Section
    st.title("📂 File Selection")
    message =""
    available_files = get_available_files(selected_folder)
    if not available_files:
        st.error(f"No CSV files found in '{selected_folder}' folder")
        st.info(f"Please add CSV files to the '{selected_folder}' folder")
        st.stop()
    # File selection options
    st.write("**File Processing Options:**")
    # Radio button for selection mode
    selection_mode = st.radio(
        "Choose selection mode:",
        ["Process All Files", "Select Specific Files"],
        index=0,  # Default to "Process All Files"
        help="Choose whether to process all files or select specific ones"
    )
    if selection_mode == "Process All Files":
        selected_files = available_files
        message = "Processed all files"
        with st.expander("View all files"):
            for file in available_files:
                st.write(f"• {file}")
    else:
        # File selection with multiselect
        st.write("**Select specific files to process:**")
        selected_files = st.multiselect(
            "Available CSV files:",
            options=available_files,
            default=[],  # Start with none selected for manual selection
            help=f"Choose which CSV files from '{selected_folder}' directory to analyze"
        )
        
        # Add select all / deselect all buttons for manual mode
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All", key="select_all"):
                st.session_state.multiselect_key = available_files
        with col2:
            if st.button("Clear All", key="clear_all"):
                st.session_state.multiselect_key = []
    # Show selected files info
    if selected_files:
        if selection_mode == "Process All Files":
            st.info(f"✅ All {len(selected_files)} files will be processed")
        else:
            st.info(f"Selected {len(selected_files)} file(s) will be processed")
            with st.expander("View selected files"):
                for file in selected_files:
                    st.write(f"• {file}")
    else:
        if selection_mode == "Select Specific Files":
            st.warning("No files selected")
        else:
            st.error("No files found to process")
    # Load data only if files are selected

    # Load data with selected files
    if st.button("Process"):
        if not selected_files:
            st.warning("⚠️ Please select at least one file from the sidebar to proceed.")
            st.stop()
        st.session_state["src_df"], st.session_state["suggest_df"], error = load_and_process_data(selected_files, selected_folder)
        if error:
            st.error(f"Error loading data: {error}")
            st.info("Please ensure you have:")
            st.info("1. Selected valid CSV files with a pattern matching one available patterns file")
            st.info("2. A 'references.csv' file with: description, category, subcategory")
            st.stop()
        else:
            st.success(message)
            st.data_editor(st.session_state["suggest_df"], width='stretch')      
elif page == "Transaction Analysis":
    st.header("💳 Transaction Analysis")
    suggest_df = st.session_state["suggest_df"]
    if st.session_state["suggest_df"] is not None:
        # Show categorized transactions        
        if len(st.session_state["suggest_df"]) > 0:
            #st.subheader("Categorized Transactions")
            display_df = st.session_state["suggest_df"][st.session_state["suggest_df"]["match_type"].isin(["exact", "manual"])].copy()
            #st.dataframe(display_df, width='stretch')
            
            # Category breakdown
            st.subheader("Category Breakdown")
            cat_summary = display_df.groupby("category")["amount"].agg(["sum", "count"]).round(2)
            cat_summary.columns = ["Total Amount", "Transaction Count"]
            cat_summary = cat_summary.sort_values("Total Amount", ascending=False)
            st.dataframe(cat_summary, width='content')
        else:
            st.info("No automatically categorized transactions found.")
elif page == "Data Review":
    st.header("🔍 Data Review")
    if st.session_state.suggest_df is not None:
        needs_review_df = st.session_state["suggest_df"][~st.session_state.suggest_df["match_type"].isin(["exact", "manual"])].copy()  
        if len(needs_review_df) > 0:
            total_transactions = len(st.session_state["suggest_df"])
            reviewed_count = len(st.session_state["suggest_df"][st.session_state["suggest_df"]["match_type"].isin(["exact","manual"])])
            if total_transactions > 0:
                progress = reviewed_count / total_transactions
                st.progress(progress, text=f"Categorization Progress: {progress:.1%}")
            st.subheader("Transactions Needing Review")
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
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1,3,1,0.75,2,2,0.5])
            with col1: st.markdown("""<div style="text-align:center; font-weight:bold; font-size:18px;">Date</div>""",
                        unsafe_allow_html=True)
            with col2: st.markdown("""<div style="text-align:center; font-weight:bold; font-size:18px;">Description</div>""",
                        unsafe_allow_html=True)
            with col3: st.markdown("""<div style="text-align:center; font-weight:bold; font-size:18px;">Amount</div>""",
                        unsafe_allow_html=True)
            with col4: st.markdown("""<div style="text-align:center; font-weight:bold; font-size:16px;
                                   padding-bottom: 2px;">Match Score</div>""",unsafe_allow_html=True)
            with col5: st.markdown("""<div style="text-align:center; font-weight:bold; font-size:18px;">Category</div>""",
                        unsafe_allow_html=True)
            with col6: st.markdown("""<div style="text-align:center; font-weight:bold; font-size:18px;">Sub-Category</div>""",
                        unsafe_allow_html=True)
            with col7: st.markdown("""<div style="text-align:center; font-weight:bold; font-size:18px;">Save</div>""",
                        unsafe_allow_html=True)     
            # Create editable table
            if len(needs_review_df) > 0:
                # Display transactions in a table with edit controls
                displayed_count = 0
                for i, (idx, row) in enumerate(st.session_state["suggest_df"].iterrows()):
                    if row.match_type == 'exact' or row.match_type == 'manual':
                        continue                       
                    # Create columns for the table-like layout
                    if displayed_count >= 20:
                        break
                    displayed_count += 1
                    with col1: 
                        styled_date = f"""<div style="
                                font-size: 17px; 
                                padding-top: 5px;
                                padding-bottom: 20px;
                                text-align: center;
                                border: 2px solid #4A90E2;
                            ">{row.date}</div>
                            """
                        st.markdown(styled_date, unsafe_allow_html=True)
                    with col2:
                        styled_description = f"""<div style="
                                font-size: 17px; 
                                padding-top: 5px;
                                padding-bottom: 20px;
                                text-align: center;
                                border: 2px solid #4A90E2;
                            ">{row.description}</div>
                            """
                        st.markdown(styled_description, unsafe_allow_html=True)
                    with col3: 
                        styled_amount= f"""<div style="
                                font-size: 17px; 
                                padding-top: 5px;
                                padding-bottom: 20px;
                                text-align: center;
                                border: 2px solid #4A90E2;
                                ">{row.amount}</div>
                                """
                        st.markdown(styled_amount, unsafe_allow_html=True)
                    with col4: 
                        styled_score= f"""<div style="
                                font-size: 17px; 
                                padding-top: 5px;
                                padding-bottom: 20px;
                                text-align: center;
                                border: 2px solid #4A90E2;
                                ">{row.match_score}</div>
                                """
                        st.markdown(styled_score, unsafe_allow_html=True)
                    with col5:
                        category_options = ["Select Category"] + existing_categories
                        default_category = row.category if row.category in category_options else "Select Category"
                        default_index = category_options.index(default_category)

                        selected_cat_option = st.selectbox(
                            "Choose Category",
                            options=category_options,
                            index=default_index,
                            key=f"cat_select_{idx}",
                            accept_new_options=True,
                            label_visibility="collapsed"
                        )
                    
                    with col6:
                        if selected_cat_option and selected_cat_option in existing_subcategories:
                            subcat_options = ["Select Sub-Category"] + existing_subcategories[selected_cat_option]
                        else:
                            subcat_options = ["Select Sub-Category"]
                        default_subcategory = row.subcategory if row.subcategory in subcat_options else "Select Sub-Category"
                        default_subindex = subcat_options.index(default_subcategory)
                        selected_subcat_option = st.selectbox(
                            "Choose Sub-Category",
                            options=subcat_options,
                            index=default_subindex,
                            key=f"subcat_select_{idx}",
                            accept_new_options=True,
                            label_visibility="collapsed"
                        )
                    
                    with col7:
                        if st.button("💾", key=f"update_{idx}", help="Save categorization"):
                            if selected_cat_option and selected_subcat_option and "Select" not in selected_cat_option and "Select" not in selected_subcat_option:
                                # Update the transaction in session state
                                st.session_state["suggest_df"]["match_type"].at[idx] = "manual"
                                st.rerun()
                            else:
                                errormsg()
        else:
            st.success("🎉 All transactions have been successfully categorized!")
            st.balloons()
elif page == "Master Data":
    st.header("🔍 Master Data Editor")
    data_to_display={"Old data":st.session_state["src_df"],"Currently parsed data":st.session_state["suggest_df"],"All data":pd.concat([st.session_state["src_df"],st.session_state["suggest_df"]],ignore_index=True)}
    data_select = st.radio("Data Selection",data_to_display,horizontal=True,index=1)
    st.write(data_select)
    if data_to_display[data_select] is not None:
        total_transactions = len(data_to_display[data_select])
        auto_categorized_count = len(data_to_display[data_select][data_to_display[data_select]["match_type"]=="exact"])
        manual_categorized_count = len(data_to_display[data_select][data_to_display[data_select]["match_type"]=="manual"])
        needs_review_count = len(data_to_display[data_select][~data_to_display[data_select]["match_type"].isin(["exact","manual"])])
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Transactions", total_transactions)
        with col2:
            st.metric("Auto-Categorized", auto_categorized_count)
        with col3:
            st.metric("User-Categorized", manual_categorized_count)
        with col4:
            st.metric("Needs Review", needs_review_count)
        st.data_editor(data_to_display[data_select], width='stretch',
                       column_order=["date","description","amount","card","category","subcategory"],
                       disabled=["date","description","amount","card"])
elif page == "Visualization":
    st.header("📈 Budget Analytics")
    if st.session_state.suggest_df is not None:
        
        if len(st.session_state.suggest_df) > 0:
            # Create and display charts
            fig = create_expense_charts(st.session_state.suggest_df)
            if fig:
                st.pyplot(fig)
            
            # Additional analytics
            st.subheader("Spending Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Top 5 Categories by Amount:**")
                cat_totals = st.session_state.suggest_df.groupby(
                            "category")["amount"].sum().sort_values(ascending=False).head()
                for cat, amount in cat_totals.items():
                    st.write(f"• {cat}: ${amount:,.2f}")
            
            with col2:
                st.write("**Top 5 Most Frequent Categories:**")
                cat_counts = st.session_state.suggest_df["category"].value_counts().head()
                for cat, count in cat_counts.items():
                    st.write(f"• {cat}: {count} transactions")
        else:
            st.info("No categorized data available for analytics. Please review transactions first.")
else:
    st.title("Welcome to the Budget Tracker App!")