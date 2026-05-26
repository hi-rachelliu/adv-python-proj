import pytest
import pandas as pd
from budget import Budget
from config import COLUMNS
from io import StringIO
from collections.abc import Generator
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from pathlib import Path
from budget import async_read_sql_query, rollover_date
from sqlalchemy.engine.base import Engine
from sqlalchemy.pool import StaticPool
import asyncio

# CONSTANTS + SETUP FIXTURES + HELPER FUNCTIONS /////////////////////

SCHEMA_PATH = "db/schema.sql"

VALID_CSV = "assets/files/lowercase.csv"
INVALID_CATEGORIES_CSV = "assets/files/invalid_categories.csv"
EMPTY_VALS_CSV = "assets/files/invalid_empty_vals.csv"
MISSING_COLS_CSV = "assets/files/invalid_missing_cols.csv"
INVALID_DATES_CSV = "assets/files/invalid_dates.csv"
NEG_AMOUNTS_CSV = "assets/files/invalid_neg_amounts.csv"

EMPTY_DF = pd.DataFrame(
    {
        "date": pd.Series(dtype="datetime64[ns]"),
        "amount": pd.Series(dtype="float"),
        "item": pd.Series(dtype="str"),
        "category": pd.Series(dtype="str"),
    }
)


@pytest.fixture()
def valid_df() -> Generator[pd.DataFrame, None, None]:
    """
    Yields a valid df based on `lowercase.csv`
    """
    with open(VALID_CSV, "r") as file:
        csv_data = file.read()
        processed = "".join(line.strip('"') for line in csv_data)
        read_df = pd.read_csv(StringIO(processed))
        read_df.columns = read_df.columns.str.lower()
        read_df.columns = read_df.columns.str.strip()
    yield read_df


@pytest.fixture
def engine(valid_df: pd.DataFrame) -> Generator[Engine, None, None]:
    """
    Yields connection to sqlalchemy engine of sqlite populated with valid
    transactions from `lowercase.csv`
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    schema_sql = Path(SCHEMA_PATH).read_text()

    with engine.begin() as conn:
        connection = conn.connection
        connection.executescript(schema_sql)
        valid_df.to_sql(name="transactions", con=conn, if_exists="append", index=False)

    yield engine


def csv_to_df(filepath: str) -> pd.DataFrame:
    """
    Returns a dataframe based on the CSV file's `filepath`
    """
    with open(filepath, "r") as file:
        csv_data = file.read()
        processed = "".join(line.strip('"') for line in csv_data)
        read_df = pd.read_csv(StringIO(processed))
        read_df.columns = read_df.columns.str.lower()
        read_df.columns = read_df.columns.str.strip()
    return read_df


# For rollover_date(), used in monthly_spending() and monthly_income_spending()
# rollover_date() rolls any date over to the first of the next month


def test_rollover_date_may():
    """
    Tests that a date_str of "2026-05-27" rolls over to "2026-06-01"
    """
    result_date = rollover_date("2026-05-27")
    assert result_date == "2026-06-01"


def test_rollover_date_december():
    """
    Tests that a date_str of "2026-12-07" rolls over to "2027-01-01"
    """
    result_date = rollover_date("2026-12-07")
    assert result_date == "2027-01-01"


# For _validate_df() /////////////////////


def test_validate_success():
    """
    Tests that _validate_df() successfully validates lowercase.csv
    """
    read_df = csv_to_df(VALID_CSV)
    df = Budget._validate_df(read_df)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == COLUMNS
    assert len(df) == 10


def test_validate_missing_required_cols():
    """
    Tests that _validate_df() raises Exception on a dataframe with missing
    required columns
    """
    read_df = csv_to_df(MISSING_COLS_CSV)

    with pytest.raises(Exception) as excinfo:
        df = Budget._validate_df(read_df)
    assert (
        str(excinfo.value)
        == "Validation Error: Missing columns: ['category']. Check that all"
        " required columns: ['date', 'amount', 'item', 'category'] are included."
    )


def test_validate_empty_vals():
    """
    Tests that _validate_df() raises Exception on a dataframe with empty values
    """
    read_df = csv_to_df(EMPTY_VALS_CSV)

    with pytest.raises(Exception) as excinfo:
        df = Budget._validate_df(read_df)
    assert (
        str(excinfo.value)
        == "Validation Error: check that your values are not empty in columns:"
        " ['amount', 'item', 'category']"
    )


def test_validate_negative_amounts():
    """
    Tests that _validate_df() raises Exception on a dataframe with negative amounts
    """
    read_df = csv_to_df(NEG_AMOUNTS_CSV)

    with pytest.raises(Exception) as excinfo:
        df = Budget._validate_df(read_df)
    assert (
        str(excinfo.value)
        == "Validation Error: transaction amounts are not valid. Check that your 'Amount' inputs are all positive."
    )


def test_validate_invalid_categories():
    """
    Tests that _validate_df() raises Exception on a dataframe with invalid categories
    """
    read_df = csv_to_df(INVALID_CATEGORIES_CSV)

    with pytest.raises(Exception) as excinfo:
        df = Budget._validate_df(read_df)
    assert (
        str(excinfo.value)
        == "Validation Error: category values ['rent', 'home + garden'] are "
        "not valid: are not one of ['groceries', 'food', 'housing', 'utilities', "
        "'gifts', 'travel', 'income', 'other']"
    )


def test_validate_invalid_dates():
    """
    Tests that _validate_df() raises Exception on a dataframe with invalid dates -
    where the csv does not have dates formatted in a date format that can be recognized
    by pandas. In this case, the date is written as a natural language string: "may first 2026"
    """
    read_df = csv_to_df(INVALID_DATES_CSV)

    with pytest.raises(Exception) as excinfo:
        df = Budget._validate_df(read_df)
    assert (
        str(excinfo.value)
        == "Validation Error: transaction dates are not valid: cannot be converted into datetime values"
    )


# FOR add_transactions() /////////////////////


def test_add_transactions_success(engine: Engine):
    """
    Tests that when add_transactions() succeeds, we add transactions into the database
    """
    dates = ["2026-05-01", "2026-05-05", "2026-04-27", "2026-05-20"]
    amounts = ["15.4", "150", "270", "2716"]
    items = ["pizza", "shopping", "birthday dinner", "salary"]
    categories = ["food", "other", "other", "income"]

    budget = Budget(eng=engine)
    before_length = len(budget.df)
    budget.add_transactions(dates, amounts, items, categories)

    # check the df is longer
    after_length = len(budget.df)
    assert after_length == before_length + 4

    # check that the data has persisted to sqlite
    with engine.begin() as conn:
        after_df = pd.read_sql_query("SELECT * FROM transactions", con=conn)

    assert len(after_df) == before_length + 4


def test_add_transactions_failure(engine: Engine):
    """
    Tests that if validation fails (in this case, because dates contains a None
    value), add_transactions() raises an Exception.

    _validate_df(), which is called in add_transactions(), is tested
    comprehensively earlier in this file. So other failure cases are omitted.
    """
    dates = [None]
    amounts = ["15.4"]
    items = ["pizza"]
    categories = ["food"]

    budget = Budget(eng=engine)
    with pytest.raises(Exception):
        budget.add_transactions(dates, amounts, items, categories)


# FOR TESTING ASYNC SQL QUERIES IN ALL FUNCTIONS  //////////////////
def test_async_read_sql_query_excludes_incomes(engine: Engine):
    """
    Tests that in async_read_sql_query(), an sql query to exclude income transactions
    excludes income transactions
    """

    sql_query = """SELECT * from transactions
                    where category != 'income' """

    df = asyncio.run(async_read_sql_query(sql_query, engine))

    assert len(df) == 9
    assert list(df["item"]) == [
        "trader joe's groceries",
        "lunch with coworkers",
        "may rent",
        "electric bill",
        "birthday gift",
        "flight to nyc",
        "coffee and pastry",
        "internet bill",
        "random shopping",
    ]
    assert list(df["category"]) == [
        "groceries",
        "food",
        "housing",
        "utilities",
        "gifts",
        "travel",
        "food",
        "utilities",
        "other",
    ]


def test_async_read_sql_query_summarize_expense(engine: Engine):
    """
    Tests that in async_read_sql_query() in summarize(), the sum() function works
    for total expenses
    """
    expense_query = """SELECT sum(amount) from transactions
                        where category <> 'income' """
    total_expense = asyncio.run(async_read_sql_query(expense_query, engine)).iloc[0, 0]
    assert total_expense == 1806.03


def test_async_read_sql_query_summarize_income(engine: Engine):
    """
    Tests that in async_read_sql_query() in summarize(), the sum() function works
    for total incomes
    """
    income_query = """SELECT sum(amount) from transactions
                        where category = 'income' """
    total_income = asyncio.run(async_read_sql_query(income_query, engine)).iloc[0, 0]
    assert total_income == 2500


def test_async_read_sql_query_monthly_spending(engine: Engine):
    """
    Tests that in async_read_sql_query() in monthly_spending(), the
    sql query works as expected
    """

    sql_query = """SELECT strftime('%Y-%m', date) AS date, sum(amount) AS amount 
                    FROM transactions
                    where category <> 'income'
                    AND date >= :from_date
                    AND date < :to_date
                    GROUP BY strftime('%Y-%m', date)
                    """

    monthly = asyncio.run(
        async_read_sql_query(
            sql_query,
            engine,
            params={"from_date": "2026-05-01", "to_date": "2026-06-01"},
        )
    )
    assert monthly["date"].iloc[0] == "2026-05"
    assert float(monthly["amount"].iloc[0]) == 1806.03


def test_async_read_sql_query_monthly_income_spending(engine: Engine):
    """
    Tests that in async_read_sql_query() in monthly_income_spending(), the
    sql query works as expected
    """
    sql_query = """SELECT strftime('%Y-%m', date) AS date, 
                    sum(amount) AS amount,
                    category = 'income' AS category
                    FROM transactions
                    WHERE date >= :from_date
                    AND date < :to_date
                    GROUP BY strftime('%Y-%m', date), category = 'income'
                    """
    income_spending_df = asyncio.run(
        async_read_sql_query(
            sql_query, engine, {"from_date": "2026-05-01", "to_date": "2026-06-01"}
        )
    )

    assert list(income_spending_df["date"]) == ["2026-05", "2026-05"]
    assert list(income_spending_df["amount"]) == [1806.03, 2500.00]
    assert list(income_spending_df["category"]) == [False, True]


# FOR get_all_expenses() and get_all_incomes() /////////////////////


@patch("budget.async_read_sql_query", new_callable=AsyncMock)
def test_get_all_expenses_formats_date(mock_async_read):
    """
    Tests that get_all_expenses() returns all expense df values from
    async_read_sql_query()
    """

    mock_async_read.return_value = pd.DataFrame(
        {
            "date": ["01.25.2025"],
            "amount": [50],
            "item": ["pizza"],
            "category": ["food"],
        }
    )

    budget = Budget()
    result_df = budget.get_all_expenses()

    assert result_df is not None
    assert isinstance(result_df, pd.DataFrame)
    assert list(result_df["date"]) == ["2025-01-25"]
    assert list(result_df["amount"]) == [50]
    assert list(result_df["item"]) == ["pizza"]
    assert list(result_df["category"]) == ["food"]


@patch("budget.async_read_sql_query", new_callable=AsyncMock)
def test_get_all_expenses_none(mock_async_read):
    """
    Tests that get_all_expenses() returns None if the df is empty
    """

    mock_async_read.return_value = EMPTY_DF

    budget = Budget()
    result_df = budget.get_all_expenses()

    assert result_df is None


@patch("budget.async_read_sql_query", new_callable=AsyncMock)
def test_get_all_incomes_formats_date(mock_async_read):
    """
    Tests that get_all_incomes() returns all income df values from
    async_read_sql_query()
    """
    mock_async_read.return_value = pd.DataFrame(
        {
            "date": ["01.23.2025"],
            "amount": [5000],
            "item": ["salary"],
            "category": ["income"],
        }
    )

    budget = Budget()
    result_df = budget.get_all_incomes()

    assert result_df is not None
    assert isinstance(result_df, pd.DataFrame)
    assert list(result_df["date"]) == ["2025-01-23"]
    assert list(result_df["amount"]) == [5000]
    assert list(result_df["item"]) == ["salary"]
    assert list(result_df["category"]) == ["income"]


@patch("budget.async_read_sql_query", new_callable=AsyncMock)
def test_get_all_incomes_none(mock_async_read):
    """
    Tests that get_all_incomes() returns None if the df is empty
    """
    mock_async_read.return_value = EMPTY_DF

    budget = Budget()
    result_df = budget.get_all_incomes()

    assert result_df is None
