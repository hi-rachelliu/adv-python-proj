from __future__ import annotations
import pandas as pd
from config import CATEGORIES, COLUMNS
from datetime import datetime
import base64
import io
from typing import Literal

JsonFrameOrient = Literal["split", "records", "index", "columns", "values", "table"]


class Budget:
    @classmethod
    def from_json(cls, json_df: str | None, orient: JsonFrameOrient | None):
        """
        Creates a budget instance from a JSON dataframe object json_df, encoded
        with `orient`
        """
        parsed_df = pd.read_json(io.StringIO(json_df), orient=orient)
        budget = Budget(df=parsed_df)
        return budget

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
            df = pd.read_csv(io.StringIO(processed), sep=",|;|:|\t|`", engine="python")

            # normalize: make lowercase + strip whitespace from
            # all columns names + category values
            df.columns = df.columns.str.lower()
            df.columns = df.columns.str.strip()

            df["category"] = df["category"].str.lower()
            df["category"] = df["category"].str.strip()

            # only include required columns, ignore extra columns
            df = df[COLUMNS]

            # TODO: run validations (correct cols/inputs) on dataframe
            # TODO: validate amounts
            # TODO: validate categories
            # TODO: date format must be valid
            # TODO: missing cols
            # TODO: uneven rows

            print(df.to_string())

        except Exception as e:
            raise Exception(f"There was an error processing this file: {e}")

        budget = Budget(df)
        return budget

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        if df is None:
            self.df = pd.DataFrame(
                {
                    "date": pd.Series(dtype="datetime64[ns]"),
                    "amount": pd.Series(dtype="float"),
                    "item": pd.Series(dtype="str"),
                    "category": pd.Series(dtype="str"),
                }
            )
        else:
            self.df = df
        try:
            self.normalize_df()
        except Exception:
            raise Exception(f"Error normalizing df: {self.df.to_string()}")

        self.row_id = 0

    def normalize_df(self) -> None:
        """
        Normalizes a dataframe
        """
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        self.df["amount"] = pd.to_numeric(self.df["amount"], errors="coerce")

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
        # TODO: make fixture dataframes for testing

        for inputs in (dates, amounts, items, categories):
            if None in inputs:
                raise Exception(
                    "Validation Error: check that your inputs are not empty. "
                    "Please fill out or delete any rows with empty inputs."
                )

        num_transactions = len(dates)

        # validate amounts
        try:
            float_amounts = [float(amount) for amount in amounts]
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
        valid_categories = all(category in CATEGORIES for category in categories)
        if not valid_categories:
            raise Exception(
                f"Validation Error: categories are not valid: are not one of {CATEGORIES}"
            )

        # date format must be valid
        try:
            format = "%Y-%m-%d"
            datetime_dates = [datetime.strptime(date, format) for date in dates]
        except Exception:
            raise Exception(
                "Validation Error: transaction dates are not valid: cannot be converted into datetime values"
            )

        new_rows = pd.DataFrame(
            {
                "date": datetime_dates,
                "amount": float_amounts,
                "item": items,
                "category": categories,
            }
        )
        self.df = pd.concat([self.df, new_rows], ignore_index=True)
        self.normalize_df()
        self.row_id += num_transactions
        return True

    def get_all_expenses(
        self, from_date_str: str = "", to_date_str: str = ""
    ) -> pd.DataFrame | None:
        """
        Gets all expenses from the database, can filter by start and end dates.
        `from_date` and `to_date` are strs that represent the start and end dates
        (inclusive) of the expenses to include.
        If both are empty strings, then the function returns all expenses.
        Returns None if the database is empty.
        """
        if not from_date_str and not to_date_str:
            df_expenses = self.df[self.df["category"] != "income"]

        elif not from_date_str or not to_date_str:
            raise Exception(
                "Validation Error: from_date and to_date must both be filled with values!"
            )

        else:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
            filtered_df = self.df[
                (self.df["date"] >= from_date) & (self.df["date"] <= to_date)
            ]
            df_expenses = filtered_df[filtered_df["category"] != "income"]

        return df_expenses.copy(deep=True) if len(df_expenses) else None

    def get_all_incomes(
        self, from_date_str: str = "", to_date_str: str = ""
    ) -> pd.DataFrame | None:
        """
        gets all incomes from the database, can filter by start and end dates.
        Returns None if the database is empty.
        """
        if not from_date_str and not to_date_str:
            df_incomes = self.df[self.df["category"] == "income"]

        elif not from_date_str or not to_date_str:
            raise Exception(
                "Validation Error: from_date and to_date must both be filled with values!"
            )

        else:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
            filtered_df = self.df[
                (self.df["date"] >= from_date) & (self.df["date"] <= to_date)
            ]
            df_incomes = filtered_df[filtered_df["category"] == "income"]

        return df_incomes.copy(deep=True) if len(df_incomes) else None

    def summarize(self) -> tuple[float, float]:
        """
        Returns the total expense and the total income
        """
        df_expenses = self.df[self.df["category"] != "income"]
        total_expense = df_expenses["amount"].sum()

        df_incomes = self.df[self.df["category"] == "income"]
        total_income = df_incomes["amount"].sum()

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
        df_expenses = self.df[self.df["category"] != "income"]
        filtered_df = df_expenses[
            (df_expenses["date"].dt.month == input_month)
            & (df_expenses["date"].dt.year == input_year)
        ]
        if len(filtered_df) == 0:
            return None
        return filtered_df

    def monthly_income_spending(self):
        """
        Returns a dataframe

        Feeds into the monthly incomes + spendings bar chart
        """
        # TODO
        pass

    def monthly_spending(self):
        """
        Returns a dataframe

        Feeds into the monthly spendings bar chart
        """
        # TODO
        pass
