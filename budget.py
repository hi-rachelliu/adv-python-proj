from __future__ import annotations
import pandas as pd
from config import CATEGORIES, COLUMNS
from datetime import datetime
import base64
import io
from typing import Literal, Any
from pathlib import Path
from sqlalchemy import create_engine, text
import asyncio

JsonFrameOrient = Literal["split", "records", "index", "columns", "values", "table"]

DATABASE_PATH = "db/budget.db"
SCHEMA_PATH = "db/schema.sql"


def setup_db():
    """
    Creates database file at startup if it doesn't exist already
    """
    schema_sql = Path(SCHEMA_PATH).read_text()

    with engine.begin() as conn:
        connection = conn.connection
        connection.executescript(schema_sql)


def sync_df_to_sql(df: pd.DataFrame) -> None:
    """
    Sync code: Tries persisting a dataframe to the sqlite database,
    replacing any current data. Raises Exception if it fails
    """
    try:
        with engine.begin() as conn:
            df.to_sql(
                name="transactions",
                con=conn,
                if_exists="replace",
                index=False,
            )
    except Exception as e:
        raise Exception(f"Error persisting df to sqlite3: {e}")


async def async_df_to_sql(df: pd.DataFrame) -> None:
    """
    Async code: persists dataframe to sqlite
    """
    return await asyncio.to_thread(sync_df_to_sql, df)


def sync_read_sql_query(
    sql_query: str, params: dict[str, Any] | None = None
) -> pd.DataFrame:
    """
    Sync code: Tries to read from sqlite database into a dataframe.
    Raises Exception if it fails
    """
    try:
        with engine.begin() as conn:
            df = pd.read_sql_query(text(sql_query), params=params, con=conn)
    except Exception as e:
        raise Exception(f"Error creating dataframe from sql query: {e}")
    return df


async def async_read_sql_query(
    sql_query: str, params: dict[str, Any] | None = None
) -> pd.DataFrame:
    """
    Async code: reads from sqlite, returns df with sqlite data
    """
    return await asyncio.to_thread(sync_read_sql_query, sql_query, params)


# ////////////////////////////////////////////////////////////////////////

Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False, future=True)
setup_db()


class SQLiteError(Exception):
    pass


class Budget:
    @staticmethod
    def _validate_rows(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates that for an input `df`:
        - all required columns are included
        - there are no empty strings in any of the required columns
        - there are no NaN values in any of the required columns
        - amounts are (or can be coerced into) floats
        - categories are only: "Groceries", "Food", "Housing", "Utilities", "Gifts", "Travel", "Income", or "Other"
        - dates are valid (can be coerced into datetime objects)
        """

        # validate all required columns are included
        required_cols_missing = [c for c in COLUMNS if c not in df.columns]
        if required_cols_missing:
            raise Exception(
                f"Validation Error: Missing columns: {required_cols_missing}. Check that all required columns: {COLUMNS} are included."
            )

        # only include required columns, ignore extra columns
        df = df[COLUMNS]

        # validate there are no empty strings in any of the required columns
        has_empty_strings = (df == "").any().any()
        if has_empty_strings:
            raise Exception("Validation Error: check that your values are not empty.")

        # validate there are no NaN values in any of the required columns
        nan_cols = df.columns[df.isna().any()].to_list()
        invalid_cols = [c for c in nan_cols if c in COLUMNS]
        if len(invalid_cols) > 0:
            raise Exception(
                f"Validation Error: check that your values are not empty in columns: {invalid_cols}"
            )

        try:
            df["category"] = df["category"].str.lower()
            df["category"] = df["category"].str.strip()
        except Exception as e:
            raise Exception(f"There was an error processing this file: {e}")

        # validate amounts
        try:
            float_amounts = [float(amount) for amount in df["amount"]]
        except Exception:
            raise Exception(
                "Validation Error: transaction amounts are not valid. "
                "Check that your have numeric values for all your "
                "'Amount' inputs."
            )

        amounts_positive = all(fl_amount > 0 for fl_amount in float_amounts)
        if not amounts_positive:
            raise Exception(
                "Validation Error: transaction amounts are not valid. Check that your"
                " 'Amount' inputs are all positive."
            )

        # validate categories
        invalid_categories = [c for c in df["category"] if c not in CATEGORIES]
        if invalid_categories:
            raise Exception(
                f"Validation Error: category values {invalid_categories} are not valid: are not one of {CATEGORIES}"
            )

        # validate dates
        try:
            datetime_dates = pd.to_datetime(df["date"])
        except Exception:
            raise Exception(
                "Validation Error: transaction dates are not valid: cannot be converted into datetime values"
            )
        return df.reset_index(drop=True)

    @classmethod
    def from_csv(cls, contents) -> Budget:
        """
        Bulk imports from csv instead of manually inputting transactions.
        Returns serialized df state.
        """
        _, content_string = contents.split(",")

        decoded = base64.b64decode(content_string)
        str_buffer = decoded.decode("utf-8")
        processed = "".join(line.strip('"') for line in str_buffer)

        try:
            # read csv
            read_df = pd.read_csv(
                io.StringIO(processed), sep=",|;|:|\t|`", engine="python"
            )

            # normalize: make lowercase + strip whitespace from
            # all columns names + category values
            read_df.columns = read_df.columns.str.lower()
            read_df.columns = read_df.columns.str.strip()
        except Exception as e:
            raise Exception(f"There was an error processing this file: {e}")

        df = Budget._validate_rows(read_df)
        budget = Budget(df)

        return budget

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        if df is None:
            read_df = pd.read_sql("SELECT * FROM transactions", engine)
            self.df = Budget._validate_rows(read_df)
        else:
            try:
                self.df = df
            except Exception as e:
                raise Exception(f"Error normalizing df: {e}")
            asyncio.run(async_df_to_sql(self.df))

    def add_transactions(
        self,
        dates: list[str],
        amounts: list[str],
        items: list[str],
        categories: list[str],
    ) -> bool:
        """
        Validates and adds multiple transactions into the database, returns a
        bool, whether or not the concatenation succeeded.
        """

        for inputs in (dates, amounts, items, categories):
            if None in inputs or "" in inputs:
                raise Exception(
                    "Validation Error: check that your inputs are not empty. "
                    "Please fill out or delete any rows with empty inputs."
                )

        # make a df from the columns and validate it
        try:
            unvalidated_rows = pd.DataFrame(
                {
                    "date": dates,
                    "amount": amounts,
                    "item": items,
                    "category": categories,
                }
            )
            new_rows = Budget._validate_rows(unvalidated_rows)
        except Exception as e:
            raise Exception(f"{e}")

        # persist the new df into sqlite
        self.df = pd.concat([self.df, new_rows], ignore_index=True)
        asyncio.run(async_df_to_sql(self.df))
        return True

    def get_all_expenses(self) -> pd.DataFrame | None:
        """
        Gets all expenses from the database.
        Returns None if the database is empty.

        Used in generate_expenses_incomes_output().
        """

        sql_query = """SELECT * from transactions
                    where category != 'income' """
        df_expenses = asyncio.run(async_read_sql_query(sql_query))

        df_expenses["date"] = pd.to_datetime(df_expenses["date"]).dt.strftime(
            "%Y-%m-%d"
        )

        return df_expenses.copy(deep=True) if len(df_expenses) else None

    def get_all_incomes(self) -> pd.DataFrame | None:
        """
        gets all incomes from the database, can filter by start and end dates.
        Returns None if the database is empty.
        """

        sql_query = """SELECT * from transactions
                    where category == 'income' """
        df_incomes = asyncio.run(async_read_sql_query(sql_query))

        df_incomes["date"] = pd.to_datetime(df_incomes["date"]).dt.strftime("%Y-%m-%d")

        return df_incomes.copy(deep=True) if len(df_incomes) else None

    def summarize(self) -> tuple[float, float]:
        """
        Returns the total expense and the total income
        """
        expense_query = """SELECT sum(amount) from transactions
                        where category <> 'income' """
        expense_res = asyncio.run(async_read_sql_query(expense_query))
        expense_scalar = expense_res.iloc[0, 0]
        total_expense = float(expense_scalar or 0.0)

        income_query = """SELECT sum(amount) from transactions
                        where category = 'income' """
        income_res = asyncio.run(async_read_sql_query(income_query))
        income_scalar = income_res.iloc[0, 0]
        total_income = float(income_scalar or 0.0)

        return total_expense, total_income

    def expenses_by_category(
        self, input_month: int, input_year: int
    ) -> pd.DataFrame | None:
        """
        Returns an expenses dataframe filtered by month, given the input_month, a number
        1 (January) to 12 (December), and the input_year, like 2026.
        If there are no transactions that particular month, returns None.

        Feeds into the expenses by category pie chart.
        """
        sql_query = """SELECT * from transactions
                        where category <> 'income' 
                        AND strftime('%m', date) = :month
                        AND strftime('%Y', date) = :year
                        """
        filtered_df = asyncio.run(
            async_read_sql_query(
                sql_query,
                params={
                    "month": f"{input_month:02d}",
                    "year": str(input_year),
                },
            )
        )

        if len(filtered_df) == 0:
            return None
        return filtered_df

    def monthly_spending(
        self, from_date_str: str, to_date_str: str
    ) -> pd.DataFrame | None:
        """
        Returns an expenses dataframe filtered by `from_date` and `to_date`, both
        formatted like %Y-%m-%d. Includes all expenses from the start of the
        `from_date` month to the end of the `to_date` month.

        Feeds into the spending, month to month chart
        """
        to_date_end = datetime.strptime(to_date_str, "%Y-%m-%d")
        if to_date_end.month == 12:
            to_date_next_day = datetime(year=to_date_end.year + 1, month=1, day=1)
        else:
            to_date_next_day = datetime(
                year=to_date_end.year, month=to_date_end.month + 1, day=1
            )

        to_date = datetime.strftime(to_date_next_day, "%Y-%m-%d")

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
                params={"from_date": from_date_str, "to_date": to_date},
            )
        )

        if len(monthly) == 0:
            return None
        return monthly

    def monthly_income_spending(self, from_date_str: str, to_date_str: str):
        """
        Returns an expenses vs. incomes dataframe filtered by `from_date` and `to_date`, both
        formatted like %Y-%m-%d. Includes all expenses and incomes from the
        start of the `from_date` month to the end of the `to_date` month.

        Feeds into the income vs. spending, month to month chart
        """
        to_date_end = datetime.strptime(to_date_str, "%Y-%m-%d")
        if to_date_end.month == 12:
            to_date_next_day = datetime(year=to_date_end.year + 1, month=1, day=1)
        else:
            to_date_next_day = datetime(
                year=to_date_end.year, month=to_date_end.month + 1, day=1
            )

        to_date = datetime.strftime(to_date_next_day, "%Y-%m-%d")

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
                sql_query, {"from_date": from_date_str, "to_date": to_date}
            )
        )

        if len(income_spending_df) == 0:
            return None
        return income_spending_df
