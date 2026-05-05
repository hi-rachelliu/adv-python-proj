from datetime import datetime
from dash import Dash, html, dcc, Input, Output, State, ALL, ctx, no_update
from budget import Budget
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash.development.base_component import Component
from config import CATEGORIES

# external_stylesheets=[dbc.themes.SKETCHY]

app = Dash()
budget = Budget()


def generate_empty_row(restart: bool = False) -> html.Div:
    """
    Returns an empty row of transaction input boxes, contained by a Div
    """

    if restart:
        budget.row_id = 0
    return html.Div(
        className="transaction-row",
        id={"type": "row", "index": budget.row_id},
        children=[
            html.Div(
                [
                    html.Label("Date"),
                    dcc.DatePickerSingle(
                        id={"type": "date-input", "index": budget.row_id},
                        date=datetime.today().strftime("%Y-%m-%d"),
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Amount (in dollars)"),
                    dcc.Input(
                        id={"type": "amount-input", "index": budget.row_id},
                        type="number",
                        placeholder=12,
                        required=True,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Item"),
                    dcc.Input(
                        id={"type": "item-input", "index": budget.row_id},
                        type="text",
                        placeholder="Pizza with friends",
                        required=True,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Category"),
                    dcc.Dropdown(
                        id={"type": "category-input", "index": budget.row_id},
                        options=[{"label": cat, "value": cat} for cat in CATEGORIES],
                        placeholder="> Select",
                    ),
                ]
            ),
            html.Button(
                "- Delete Row",
                id={"type": "delete-row", "index": budget.row_id},
                n_clicks=0,
            )
            if not restart
            else None,
        ],
    )


def transaction_elements() -> list[Component]:
    """
    Returns a list of HTML elements, for rendering transaction data entry
    """
    return [
        html.H2("enter data:"),
        html.P("Enter a new transaction below"),
        html.Div(children=[generate_empty_row(restart=True)], id="rows"),
        html.Button("+ Add Row", id="add-row-button", n_clicks=0),
        html.Button("Submit", id="transaction-submit", n_clicks=0),
        html.H3("Expenses"),
        html.Div(id="df-expenses", children=[html.P("No expenses yet")]),
        html.H3("Incomes"),
        html.Div(
            id="df-incomes",
            children=[html.P("No incomes yet")],
            style={"marginBottom": "50px"},
        ),
    ]


def import_csv_elements() -> list[Component]:
    """
    Returns a list of HTML elements, for rendering the import csv section
    """
    return [
        html.H2("or export from csv:"),
        html.P(
            "Dates must be formatted as %Y-%m-%d, that is, May 1st, 2026 becomes 2026-05-01."
        ),
        html.P(
            "Columns must be: Date, Amount, Item, Category (uppercase, in this exact order)."
        ),
        html.P("""In the Category column, values can only be one of the following: 
               "Groceries", "Food", "Housing", "Utilities", "Gifts", "Travel", 
               "Income", "Other"."""),
        dcc.Upload(
            id="upload-csv",
            children=html.Div(
                ["Drag and Drop or ", html.A("Select Files")],
            ),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
            accept=".csv",
        ),
        html.Button(
            id="upload-csv-submit",
            children="Submit File",
            style={"marginBottom": "50px"},
        ),
    ]


def pie_chart_elements() -> list[Component]:
    """
    Returns a list of HTML elements, for rendering the spending categories pie chart
    """
    return [
        html.H2("spendings by categories for a particular month"),
        dmc.MonthPickerInput(
            label="Pick a month", placeholder="Select month", id="month-picker"
        ),
        dcc.Graph(id="pie-chart", style={"marginBottom": "20px"}),
    ]


def spending_chart_elements() -> list[Component]:
    """
    Returns a list of HTML elements, for rendering the month-to-month spending
    bar chart
    """
    return [
        dmc.MonthPickerInput(
            type="range",
            id="spending-range",
            label="Pick months range",
            placeholder="Pick dates range",
        ),
        html.P("Not implemented yet", style={"marginBottom": "20px"}),
    ]


def spending_income_chart_elements() -> list[Component]:
    """
    Returns a list of HTML elements, for rendering the month-to-month income vs.
    spending bar chart
    """
    return [
        dmc.MonthPickerInput(
            type="range",
            id="income-spending-range",
            label="Pick months range",
            placeholder="Pick dates range",
        ),
        html.P("Not implemented yet", style={"marginBottom": "20px"}),
    ]


app.layout = dmc.MantineProvider(
    children=[
        html.H1("my budget app/data"),
        *transaction_elements(),
        *import_csv_elements(),
        html.H1("my budget app/summary"),
        *pie_chart_elements(),
        html.H2("spending, month to month"),
        *spending_chart_elements(),
        html.H2("income vs. spending, month to month"),
        *spending_income_chart_elements(),
    ],
)


def generate_expenses_incomes_output(budget: Budget):
    """
    Given the budget instance, returns the expenses output and the incomes output
    """
    expenses_df = budget.get_all_expenses()

    if expenses_df is not None:
        # modify a copy of expenses data to be more readable
        expenses_df["Date"] = expenses_df["Date"].apply(
            lambda x: x.strftime("%Y-%m-%d")
        )
        expenses_df["Amount"] = expenses_df["Amount"].apply(lambda x: f"${x}")

    incomes_df = budget.get_all_incomes()
    if incomes_df is not None:
        # modify a copy of incomes data to be more readable
        incomes_df["Date"] = incomes_df["Date"].apply(lambda x: x.strftime("%Y-%m-%d"))
        incomes_df["Amount"] = incomes_df["Amount"].apply(lambda x: f"${x}")

    total_expense, total_income = budget.summarize()
    expenses_output = (
        no_update
        if expenses_df is None
        else [
            dbc.Table.from_dataframe(expenses_df),
            html.Hr(style={"height": "2px"}),
            html.Strong("total expense: "),
            html.Span(f"${total_expense}"),
        ]
    )
    incomes_output = (
        no_update
        if incomes_df is None
        else [
            dbc.Table.from_dataframe(incomes_df),
            html.Hr(style={"height": "2px"}),
            html.Strong("total income: "),
            html.Span(f"${total_income}"),
        ]
    )
    return expenses_output, incomes_output


@app.callback(
    [
        Output("df-expenses", "children"),
        Output("df-incomes", "children"),
        Output("rows", "children"),
    ],
    [
        Input("transaction-submit", "n_clicks"),
        Input("add-row-button", "n_clicks"),
        Input({"type": "delete-row", "index": ALL}, "n_clicks"),
        Input("upload-csv-submit", "n_clicks"),
    ],
    [
        State("upload-csv", "contents"),
        State({"type": "date-input", "index": ALL}, "date"),
        State({"type": "amount-input", "index": ALL}, "value"),
        State({"type": "item-input", "index": ALL}, "value"),
        State({"type": "category-input", "index": ALL}, "value"),
        State("rows", "children"),
    ],
    prevent_initial_call=True,
)
def update_dataframe(
    _1,
    _2,
    _3,
    _4,
    contents,
    dates,
    amounts,
    items,
    categories,
    existing_rows,
):
    triggered_id = ctx.triggered_id

    if triggered_id == "transaction-submit":
        # submit transactions
        success = budget.add_transactions(dates, amounts, items, categories)
        if not success:
            raise Exception("Adding transactions not successful.")

        expenses_output, incomes_output = generate_expenses_incomes_output(budget)

        return (
            expenses_output,
            incomes_output,
            [generate_empty_row(restart=True)],
        )

    elif triggered_id == "add-row-button":
        # add an empty row
        budget.row_id += 1
        return no_update, no_update, existing_rows + [generate_empty_row()]

    elif triggered_id == "upload-csv-submit" and contents is not None:
        # uploading data from csv
        budget = Budget.import_csv(contents)
        expenses_output, incomes_output = generate_expenses_incomes_output(budget)
        return (
            expenses_output,
            incomes_output,
            [generate_empty_row(restart=True)],
        )

    else:
        # delete a row
        row_to_delete = triggered_id["index"]
        updated_rows = [
            row for row in existing_rows if row["props"]["id"]["index"] != row_to_delete
        ]
        return no_update, no_update, updated_rows


# generates a pie chart based of the money amounts in the df, separated by categories
@app.callback(
    Output("pie-chart", "figure"),
    Input("transaction-submit", "n_clicks"),
    Input("month-picker", "value"),
)
def generate_pie(_, input_month):

    if input_month is not None:
        input_date = datetime.strptime(input_month, "%Y-%m-%d")
        filtered_df_by_month = budget.expenses_by_category(
            input_date.month, input_date.year
        )

    if input_month is None or filtered_df_by_month is None:
        # return an empty graph with a note to add transactions
        fig = go.Figure()
        fig.update_layout(
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[
                {
                    "text": "Please add transactions for this month to see graphics",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 16},
                }
            ],
        )

    else:
        fig = px.pie(filtered_df_by_month, values="Amount", names="Category", hole=0.3)

    return fig


# @app.callback()
# def generate_spending_chart():
#     pass


# @app.callback()
# def generate_spending_income_chart():
#     pass


if __name__ == "__main__":
    app.run(debug=True)
