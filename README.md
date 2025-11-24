# 💰 Personal Budget Tracker

A Streamlit app for tracking and categorizing personal transactions, with manual and automatic review, file selection, and analytics.

## Features

- **Folder & File Selection:** Choose any folder and CSV files for analysis.
- **Pattern-Based Parsing:** Uses a patterns file for parsing credit card statements into a standardized format.
- **Automatic & Manual Categorization:** Transactions are auto-categorized using reference data; unmatched transactions can be manually reviewed and categorized by user.
- **Category/Subcategory Management:** Categories and subcategories are loaded from `categories.json` and can be extended/modified by the user during review.
- **Analytics:** Visualizes spending by category and subcategory with charts.

## How It Works

1. **Process Inputs:**  
    - Select a folder and CSV files.
    - Click "Process" to parse and categorize transactions.
    - Data is loaded and displayed for review.

2. **Transaction Analysis:**  
    - View transactions that are already categorized (exact/manual).
    - See breakdowns by category.

3. **Data Review:**  
    - Review and categorize unmatched transactions.
    - Select category/subcategory from dropdowns (with "Add New" options).
    - Save changes with the 💾 button.
    - Progress bar shows review completion.

4. **Master Data:**  
    - View all data (old, parsed, combined).
    - See metrics for auto/manual/needs review.
    - Edit any errors or make wholesale changes.

5. **Visualization:**  
    - Charts for category and subcategory spending.
    - Top categories and insights.

## File Structure

- `app.py`: Main Streamlit app.
- `categories.json`: Category and subcategory definitions.
- `references.csv`: Stores transaction patterns and user categorizations.
- `Patterns.csv`: Parsing patterns for transactions.
- `Source files/`: Folder for your CSV transaction files.

## Adding Categories/Subcategories

- In Data Review, select "Add New Category" or "Add New Sub-Category" in dropdowns.
- Enter the new value; it will be added to `categories.json` and used for future matching.

## Requirements

- Python 3.7+
- `streamlit`, `pandas`, `numpy`, `matplotlib`, `rapidfuzz`

## Usage

```bash
streamlit run app.py
```

Follow the sidebar to select files, process data, review/categorize transactions, and view analytics.

   Create the following structure:
   ```
   BudgetApp/
   ├── app.py
   ├── main.py
   ├── categories.json
   ├── references.csv (optional, will be created automatically)
   └── Source files/          # Or any folder name you prefer
       ├── transactions_1.csv
       ├── transactions_2.csv
       └── ...
   ```

### Required File Formats

#### CSV Transaction Files
Your CSV files should contain at least these columns (case-insensitive):
- `date`: Transaction date
- `description`: Transaction description
- `amount`: Transaction amount (positive numbers)

and must contain data in a table with headers. The header row must be input as a row in the patterns.csv file with the first column being the name or an identifier for the account/card followed by the header


#### categories.json (Pre-configured)
The app uses predefined categories from `categories.json`:
- Food (Groceries, Restaurants, Liquor)
- Travel (Parking, Gas, Tolls/fees, Car costs)
- Shopping (Clothing, Electronics, Home improvements, Supermarkets)
- TBNP (Entertainment, Hobbies, Gifts)
- Vacation (Lodging, Flights, Activities)
- Housing (Rent/Mortgage, Utilities, Repairs)
- Bank Transactions (Savings, Interest/Dividend, Payments and Transfers)
- Personal Care (Beauty, Medical)

## 🎮 How to Use

### 1. Start the Application
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### 2. Select Your Data

#### **📁 Choose Folder**
- Use the sidebar to select which folder contains your CSV files
- The app scans for all folders in your BudgetApp directory

#### **📂 Choose Files**
- **Process All Files**: Automatically processes all CSV files in the selected folder (recommended)
- **Select Specific Files**: Choose individual files for analysis

### 3. Navigate Through Pages

#### **📊 Dashboard**
- View key metrics: Total transactions, amounts, categorization progress
- See file breakdown by source
- Monitor categorization progress with a progress bar

#### **💳 Transaction Analysis** 
- View all successfully categorized transactions
- See category breakdowns with totals and counts
- Filter and analyze your spending patterns

#### **🔍 Data Review**
- **Most Important Page**: Review transactions that couldn't be automatically categorized
- For each unmatched transaction:
  1. Review transaction details (date, description, amount)
  2. Select appropriate category from dropdown
  3. Select sub-category (filtered based on category)
  4. Click "💾 Update" to save
- Click "🔄 Refresh Analysis" to see updated results across all pages

#### **📈 Analytics**
- Interactive pie charts showing expense breakdowns
- Overall category distribution
- Detailed sub-category breakdowns for top 4 categories
- Spending insights and top categories

### 4. Adding New Categories

If you need to add categories not in the predefined list:

1. Go to **Data Review** page
2. For any transaction, select "Add New Category" 
3. Enter your custom category name
4. Select "Add New Sub-Category" and enter sub-category
5. Click Update

The new category will be:
- ✅ Added to `categories.json` for future use
- ✅ Saved to `references.csv` for pattern matching
- ✅ Available immediately in all dropdowns

## 📁 File Structure

```
BudgetApp/
├── app.py                 # Main Streamlit application
├── main.py               # Core logic (can run standalone)
├── categories.json       # Predefined category structure
├── references.csv        # Auto-generated transaction patterns
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── Source files/        # Default folder for CSV files
    ├── file1.csv
    ├── file2.csv
    └── ...
```

## 🔧 Configuration

### Custom Categories
Edit `categories.json` to modify the predefined category structure:

```json
{
    "categories": [
        {
            "category": "Your Category",
            "subcategories": [
                "Subcategory 1",
                "Subcategory 2"
            ]
        }
    ]
}
```

### References File
`references.csv` is automatically created and updated. It stores:
- Transaction descriptions
- Their assigned categories and sub-categories
- Used for fuzzy matching future transactions

## 💡 Tips for Best Results

1. **Consistent Descriptions**: The app learns from transaction descriptions, so consistent merchant names work best
2. **Regular Review**: Check the Data Review page regularly to improve auto-categorization
3. **Batch Processing**: Use "Process All Files" for comprehensive analysis
4. **Category Organization**: Stick to the predefined categories for consistency
5. **File Organization**: Organize CSV files by month/year in separate folders for easier management

## 🛠️ Troubleshooting

### Common Issues

**"No CSV files found"**
- Ensure your CSV files are in the selected folder
- Check that files have `.csv` extension
- Verify files contain required columns: date, description, amount, card

**"Missing required columns"**
- Check CSV file headers match: date, description, amount, card (case-insensitive)
- Ensure no missing column headers

**"Reference file not found"**
- This is normal on first run - the app will create `references.csv` automatically
- Make sure `categories.json` exists in the project directory

**App won't start**
- Ensure all packages are installed: `pip install streamlit pandas numpy matplotlib rapidfuzz`
- Check Python version is 3.7+
- Run from the correct directory containing `app.py`

## 🔄 Workflow Example

1. **Setup**: Place your bank CSV exports in "Source files" folder
2. **Run**: Start app with `streamlit run app.py`
3. **Select**: Choose folder and files (or use "Process All Files")
4. **Review**: Check Dashboard for overview
5. **Categorize**: Go to Data Review and categorize unmatched transactions
6. **Refresh**: Click "Refresh Analysis" to update all pages
7. **Analyze**: Use Analytics page to understand spending patterns
8. **Repeat**: Add new files regularly and the app will learn your patterns

## 📊 Understanding the Output

- **Exact Match**: Transaction description exactly matches a known pattern
- **Fuzzy Match**: Transaction description is similar to a known pattern (90%+ similarity)
- **No Match**: Transaction needs manual review
- **Match Score**: Percentage similarity for fuzzy matches

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the application.


