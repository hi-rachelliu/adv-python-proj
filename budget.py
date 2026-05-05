from __future__ import annotations
import pandas as pd
from config import CATEGORIES
from datetime import datetime
import base64
import io


class Budget:
    @classmethod
    def import_csv(cls, contents) -> Budget:
        """
        Bulk imports from csv instead of manually inputting transactions.
        Returns an instance of the class Budget.
        """
        _, content_string = contents.split(",")

        decoded = base64.b64decode(content_string)
        str_buffer = decoded.decode("utf-8")
        processed = "".join(line.strip('"') for line in str_buffer)

        try:
            df = pd.read_csv(io.StringIO(processed))
        except Exception as e:
            raise Exception(f"There was an error processing this file: {e}")
        #  TODO: handle exceptions in the UI!

        budget = Budget(df)
        return budget

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        if df is None:
            self.df = pd.DataFrame(
                {
                    "Date": pd.Series(dtype="datetime64[ns]"),
                    "Amount": pd.Series(dtype="float"),
                    "Item": pd.Series(dtype="str"),
                    "Category": pd.Series(dtype="str"),
                }
            )
        else:
            self.df = df
        try:
            self.normalize_df()
        except Exception:
            raise Exception(f"Error normalizing df: {self.df.to_string()}")
        print(self.df.to_string())
        print(self.df.dtypes)
        self.row_id = 0

    def normalize_df(self) -> None:
        """
        Normalizes the Date column be datetime types and Amount column to numeric types
        """
        self.df["Date"] = pd.to_datetime(self.df["Date"], errors="coerce")
        self.df["Amount"] = pd.to_numeric(self.df["Amount"], errors="coerce")

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

        set = {len(dates), len(amounts), len(items), len(categories)}
        if len(set) != 1:
            print(
                "Validation Error: transactions are not valid: not the same number of attributes"
            )
            return False

        num_transactions = len(dates)

        # validate amounts
        try:
            float_amounts = [float(amount) for amount in amounts]
        except Exception:
            print("transaction amounts are not valid: are not numeric values")
            return False
        amounts_positive = all(fl_amount > 0 for fl_amount in float_amounts)
        if not amounts_positive:
            print(
                "Validation Error: transaction amounts are not valid: are not all positive amounts"
            )
            return False

        # validate categories
        valid_categories = all(category in CATEGORIES for category in categories)
        if not valid_categories:
            print(
                f"Validation Error: categories are not valid: are not one of {CATEGORIES}"
            )
            return False

        # date format must be valid
        try:
            format = "%Y-%m-%d"
            datetime_dates = [datetime.strptime(date, format) for date in dates]
        except Exception:
            print(
                "Validation Error: transaction dates are not valid: cannot be converted into datetime values"
            )
            return False

        new_rows = pd.DataFrame(
            {
                "Date": datetime_dates,
                "Amount": float_amounts,
                "Item": items,
                "Category": categories,
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
            df_expenses = self.df[self.df["Category"] != "Income"]

        elif not from_date_str or not to_date_str:
            raise Exception(
                "Validation Error: from_date and to_date must both be filled with values!"
            )

        else:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
            filtered_df = self.df[
                (self.df["Date"] >= from_date) & (self.df["Date"] <= to_date)
            ]
            df_expenses = filtered_df[filtered_df["Category"] != "Income"]

        return df_expenses.copy(deep=True) if len(df_expenses) else None

    def get_all_incomes(
        self, from_date_str: str = "", to_date_str: str = ""
    ) -> pd.DataFrame | None:
        """
        gets all incomes from the database, can filter by start and end dates.
        Returns None if the database is empty.
        """
        if not from_date_str and not to_date_str:
            df_incomes = self.df[self.df["Category"] == "Income"]

        elif not from_date_str or not to_date_str:
            raise Exception(
                "Validation Error: from_date and to_date must both be filled with values!"
            )

        else:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
            filtered_df = self.df[
                (self.df["Date"] >= from_date) & (self.df["Date"] <= to_date)
            ]
            df_incomes = filtered_df[filtered_df["Category"] == "Income"]

        return df_incomes.copy(deep=True) if len(df_incomes) else None

    def summarize(self) -> tuple[float, float]:
        """
        Returns the total expense and the total income
        """
        df_expenses = self.df[self.df["Category"] != "Income"]
        total_expense = df_expenses["Amount"].sum()

        df_incomes = self.df[self.df["Category"] == "Income"]
        total_income = df_incomes["Amount"].sum()

        return total_expense, total_income

    def expenses_by_category(
        self, input_month: int, input_year: int
    ) -> pd.DataFrame | None:
        """
        Returns a dataframe filtered by month, given the input_month, a number
        1 (January) to 12 (December), and the input_year, like 2026.
        If there are no transactions that particular month, returns None.

        Feeds into the expenses by category pie chart.
        """
        filtered_df = self.df[
            (self.df["Date"].dt.month == input_month)
            & (self.df["Date"].dt.year == input_year)
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
