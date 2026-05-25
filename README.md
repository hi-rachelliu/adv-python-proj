## README

Welcome to my budget app! This budget app allows you to manually transactions or import them from a CSV file, then see pie charts and bar charts that summarize your spending and income.

# Getting Set Up

After cloning this Github repo, run 'uv sync'. This should download all the project dependencies.

To run the app locally, use `uv run dash_app.py`.

The app persists data in a local sqlite database, which means unless you ovewrite existing data with a newly uploaded CSV, earlier data remains even after browser refresh.

Happy budgeting!

# Sample CSV files

In the `assets/files` files folder, there are many sample CSV files for you to test the app with, both valid and invalid.

They include:

- `capitalized.csv`
- `invalid_dates.csv`
- `lowercase.csv`
- `diff_dates.csv`
- `invalid_empty_vals.csv`
- `mult_months.csv`: contains 3 months of data, Jan to March. Recommend using this to see proper month to month data in the graphs!
- `diff_order_cols.csv`
- `invalid_missing_cols.csv`
- `semicolon_delimiter.csv`
- `extra_cols.csv`
- `invalid_neg_amounts.csv`
- `tab_delimiter.csv`
- `invalid_categories.csv`
- `invalid_uneven_rows.csv`

All invalid CSVs will raise an error in the budget app, and are prefaced with `invalid_`. All other files are valid. The titles are also descriptive of how each CSV is different.
