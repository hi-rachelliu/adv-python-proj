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

app = Dash(external_stylesheets=[dbc.themes.SKETCHY])
row_id = 0


def generate_empty_row(restart: bool = False) -> html.Div:
    """
    Returns an empty row of transaction input boxes, contained by a Div
    """

    if restart:
        global row_id
        row_id = 0
    return html.Div(
        className="transaction-row",
        id={"type": "row", "index": row_id},
        children=[
            html.Div(
                [
                    html.Label("Date"),
                    dcc.DatePickerSingle(
                        id={"type": "date-input", "index": row_id},
                        date=datetime.today().strftime("%Y-%m-%d"),
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Amount (in dollars)"),
                    dcc.Input(
                        id={"type": "amount-input", "index": row_id},
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
                        id={"type": "item-input", "index": row_id},
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
                        id={"type": "category-input", "index": row_id},
                        options=[{"label": cat, "value": cat} for cat in CATEGORIES],
                        placeholder="> Select",
                    ),
                ]
            ),
            html.Button(
                "- Delete Row",
                id={"type": "delete-row", "index": row_id},
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
        html.H2("enter data:", style={"marginTop": "20px"}),
        html.P("Enter a new transaction below"),
        html.Div(children=[generate_empty_row(restart=True)], id="rows"),
        html.Button("+ Add Row", id="add-row-button", n_clicks=0),
        html.Button(
            "Submit",
            id="transaction-submit",
            n_clicks=0,
            style={"marginBottom": "50px"},
        ),
        html.H3("Expenses"),
        html.Div(id="df-expenses", children=[html.P("No expenses yet")]),
        html.H3("Incomes", style={"marginTop": "20px"}),
        html.Div(
            id="df-incomes",
            children=[html.P("No incomes yet")],
            style={"marginBottom": "50px"},
        ),
    ]


def from_csv_elements() -> list[Component]:
    """
    Returns a list of HTML elements, for rendering the import csv section
    """
    return [
        html.H2("or export from csv:"),
        html.P(html.Strong("This overwrites any existing transactions!")),
        html.P("File requirements for your CSV: "),
        html.Ul(
            children=[
                html.Li(
                    "Columns must include: Date, Amount, Item, Category (case insensitive). Extra columns are ignored."
                ),
                html.Li("""In the Category column, values can only be one of the following: 
               "Groceries", "Food", "Housing", "Utilities", "Gifts", "Travel", 
               "Income", or "Other" (case insensitive)."""),
            ]
        ),
        dcc.Upload(
            id="upload-csv",
            children=html.Div(
                [
                    "Drag and Drop or ",
                    html.A("Select File"),
                    html.Span(id="upload-status"),
                ],
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
        ),
        html.Strong(
            html.P(
                id="upload-csv-message", children=[], style={"marginBottom": "50px"}
            ),
        ),
    ]


def pie_chart_elements() -> list[Component]:
    """
    Returns a list of HTML elements, for rendering the spending categories pie chart
    """
    return [
        html.H2(
            "spendings by categories for a particular month",
            style={"marginTop": "20px"},
        ),
        dmc.MonthPickerInput(
            label="Pick a month", placeholder="Select month", id="month-picker"
        ),
        html.Div(id="summary-pie"),
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
    html.Div(
        children=[
            dcc.Store(id="df-state"),
            html.H1("my budget app/data"),
            *transaction_elements(),
            *from_csv_elements(),
            html.H1("my budget app/summary"),
            *pie_chart_elements(),
            html.H2("spending, month to month"),
            *spending_chart_elements(),
            html.H2("income vs. spending, month to month"),
            *spending_income_chart_elements(),
        ],
        style={"marginLeft": "20px"},
    )
)


def generate_expenses_incomes_output(budget: Budget):
    """
    Given the budget instance, returns the expenses output and the incomes output
    """
    expenses_df = budget.get_all_expenses()

    if expenses_df is not None:
        # modify a copy of expenses data to be more readable
        expenses_df["date"] = expenses_df["date"].apply(
            lambda x: x.strftime("%Y-%m-%d")
        )
        expenses_df["amount"] = expenses_df["amount"].apply(lambda x: f"${x}")
        expenses_df.columns = expenses_df.columns.str.capitalize()

    incomes_df = budget.get_all_incomes()
    if incomes_df is not None:
        # modify a copy of incomes data to be more readable
        incomes_df["date"] = incomes_df["date"].apply(lambda x: x.strftime("%Y-%m-%d"))
        incomes_df["amount"] = incomes_df["amount"].apply(lambda x: f"${x}")
        incomes_df.columns = incomes_df.columns.str.capitalize()

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
        Output("df-state", "data"),
        Output("upload-csv-message", "children"),
        Output("upload-status", "children"),
    ],
    [
        Input("transaction-submit", "n_clicks"),
        Input("add-row-button", "n_clicks"),
        Input({"type": "delete-row", "index": ALL}, "n_clicks"),
        Input("upload-csv-submit", "n_clicks"),
        Input("upload-csv", "filename"),
        Input("df-state", "data"),
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
    uploaded_csv_filename,
    json_df,
    contents,
    dates,
    amounts,
    items,
    categories,
    existing_rows,
):

    triggered_id = ctx.triggered_id

    # create df from JSON data in dcc.store
    if json_df is not None:
        budget = Budget.from_json(json_df, orient="records")
    else:
        budget = Budget()

    # shows the selected filename on the file uploader
    if triggered_id == "upload-csv":
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            f": {uploaded_csv_filename}",
        )

    if triggered_id == "transaction-submit":
        # submit transactions
        budget.add_transactions(dates, amounts, items, categories)
        expenses_output, incomes_output = generate_expenses_incomes_output(budget)

        return (
            expenses_output,
            incomes_output,
            [generate_empty_row(restart=True)],
            budget.df.to_json(orient="records"),
            "",
            no_update,
        )

    elif triggered_id == "add-row-button":
        # add an empty row
        global row_id
        row_id += 1
        return (
            no_update,
            no_update,
            existing_rows + [generate_empty_row()],
            no_update,
            "",
            no_update,
        )

    elif triggered_id == "upload-csv-submit" and contents is not None:
        # uploading data from csv
        csv_budget = Budget.from_csv(contents)
        expenses_output, incomes_output = generate_expenses_incomes_output(csv_budget)
        return (
            expenses_output,
            incomes_output,
            [generate_empty_row(restart=True)],
            csv_budget.df.to_json(orient="records"),
            "Successfully uploaded from CSV file! See your transactions above.",
            "",
        )

    elif triggered_id == "upload-csv-submit" and contents is None:
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            "Error: please upload a valid CSV file first before submitting!",
            "",
        )

    else:
        print(triggered_id)
        # delete a row
        row_to_delete = triggered_id["index"]
        updated_rows = [
            row for row in existing_rows if row["props"]["id"]["index"] != row_to_delete
        ]
        return (no_update, no_update, updated_rows, no_update, "", no_update)


# generates a pie chart based of the money amounts in the df, separated by categories
@app.callback(
    Output("pie-chart", "figure"),
    Output("summary-pie", "children"),
    Input("transaction-submit", "n_clicks"),
    Input("month-picker", "value"),
    Input("df-state", "data"),
)
def generate_pie(_, input_month, json_df):

    if input_month is not None:
        if json_df is not None:
            budget = Budget.from_json(json_df, orient="records")
        else:
            budget = Budget()

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
        summary = html.Div()

    else:
        fig = px.pie(filtered_df_by_month, values="amount", names="category", hole=0.3)

        total_amount = filtered_df_by_month["amount"].sum()
        grouped_categories = filtered_df_by_month.groupby(["category"])["amount"].sum()
        grouped_df = grouped_categories.to_frame().reset_index()
        grouped_df["amount"] = grouped_df["amount"].apply(lambda x: f"${x}")
        grouped_df.columns = grouped_df.columns.str.capitalize()

        summary = html.Div(
            children=[
                html.P(html.Strong("Summary:"), style={"marginTop": "20px"}),
                html.P(f"Total spending: ${total_amount}"),
                dbc.Table.from_dataframe(grouped_df),
            ]
        )

    return fig, summary


# @app.callback()
# def generate_spending_chart():
#     pass


# @app.callback()
# def generate_spending_income_chart():
#     pass


if __name__ == "__main__":
    app.run(debug=True)
