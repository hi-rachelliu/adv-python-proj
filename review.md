## Review

**Who reviewed your code / when?**

Reviewer: Alejandro Armas Braithwaite, May 18,

**Link to the git commit and files in question (be sure to include the git commit hash to denote the specific version of the project reviewed)**

I asked him to review from_csv(), the constructor, add_transactions(), get_all_expenses(), get_all_incomes() in the Budget class in budget.py.

https://github.com/hi-rachelliu/adv-python-proj/commit/b1451f5c6185b15c91babb2fc1466c32a133763d

**Provide your reviewer with 2-3 questions you'd like them to focus on, and include those here.**

1. Is there anything that I’m missing in the validation in from_csv() or add_transactions()?
2. I also repeat somewhat similar validation code twice, but because the inputs between from_csv() or add_transactions() are slightly different. Is there a way for me to condense this?

**The reviewer's response:**

For from_csv():

    
Probably it might not be able to catch empty string, if you add something like (df[COLUMNS].astype(str).str.strip() == "") you could also check for that.

Also for the first part if you want to take the quotes at the end of the line and only the end right now:

```
processed = "".join(line.strip('"') for line in str_buffer) would delete every quote because it goes char by char.
```

Regarding add_transaction():
I would probably add a length check to assert that for a list of amount we have the same lenght of dates. Also none in imput misses empty string.

For the second question I was thinking the same, you could create a method and give both methods the same of input before validating to be able to use this. Maybe the method could look something like this:

```
REQUIRED_DATE_FORMAT = "%Y-%m-%d"

@staticmethod
def \_validate_new_rows(df: pd.DataFrame) -> pd.DataFrame:
"""Validates and returns a normalized df with the required columns."""
missing = [c for c in COLUMNS if c not in df.columns]
if missing:
raise ValueError(f"Missing required columns: {missing}")

    df = df[COLUMNS].copy()
    df["category"] = df["category"].astype(str).str.lower().str.strip()
    df["item"] = df["item"].astype(str).str.strip()

    blank_mask = df[COLUMNS].apply(
        lambda col: col.isna() | (col.astype(str).str.strip() == "")
    ).any(axis=1)
    if blank_mask.any():
        raise ValueError(f"Empty values in rows: {df.index[blank_mask].tolist()}")

    amounts = pd.to_numeric(df["amount"], errors="coerce")
    if amounts.isna().any():
        raise ValueError("Non-numeric amounts present.")
    if (amounts <= 0).any():
        raise ValueError("All amounts must be positive.")
    df["amount"] = amounts

    bad_cats = set(df["category"]) - set(CATEGORIES)
    if bad_cats:
        raise ValueError(f"Invalid categories: {bad_cats}")

    try:
        df["date"] = pd.to_datetime(df["date"], format=REQUIRED_DATE_FORMAT)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid dates: {e}") from e

    return df
```

And then to apply it to from_Csv:

```
def from_csv(cls, contents) -> Budget:
df = cls.\_parse_csv_payload(contents)
df = cls.\_validate_new_rows(df) return cls(df)
```

Or to add_transaction:

```
def add_transactions(self, dates, amounts, items, categories) -> bool:
if not (len(dates) == len(amounts) == len(items) == len(categories)):
     raise ValueError("Input lists must have equal length.")
new_rows = pd.DataFrame( {"date": dates, "amount": amounts, "item": items, "category": categories} )
new_rows = self.\_validate_new_rows(new_rows)
self.df = pd.concat([self.df, new_rows], ignore_index=True)
self.row_id += len(new_rows)
return True
```

**What, if any, changes did this review lead to you making to your code.**

In `from_csv()` and `add_transaction()`, added validation based on his feedback: error catching empty strings in values.

Combine similar validation from code from `from_csv()` and `add_transaction()` into \_validate_rows static method, as per his suggestion.
