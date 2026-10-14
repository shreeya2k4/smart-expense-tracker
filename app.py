
import calendar
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    CATEGORIES,
    init_db,
    add_transaction,
    get_transactions,
    update_transaction,
    delete_transaction,
    save_budget,
    get_budgets,
    delete_budget,
)

st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰",
    layout="wide",
)

init_db()

st.title("💰 Smart Personal Expense Tracker")
st.caption(
    "Track your money, monitor budgets and understand your spending."
)

# -------------------- Load data --------------------

transactions = get_transactions()

df = pd.DataFrame(
    transactions,
    columns=[
        "id",
        "date",
        "transaction_type",
        "category",
        "amount",
        "description",
    ],
)


if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"])

# -------------------- Sidebar --------------------

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Open page",
    [
        "Dashboard",
        "Add Transaction",
        "Manage Transactions",
        "Budget Planner",
        "Reports & Insights",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Smart Expense Tracker | BCA Mini-Project")


# -------------------- Helper functions --------------------

def money(value):
    return f"₹{value:,.2f}"


def month_data(month_string):
    if df.empty:
        return df.copy()

    return df[df["date"].dt.strftime("%Y-%m") == month_string].copy()


def calculate_totals(data):
    if data.empty:
        return 0.0, 0.0

    income = data.loc[
        data["transaction_type"] == "Income", "amount"
    ].sum()

    expenses = data.loc[
        data["transaction_type"] == "Expense", "amount"
    ].sum()

    return float(income), float(expenses)


today = date.today()
current_month = today.strftime("%Y-%m")
current_data = month_data(current_month)
income, expenses = calculate_totals(current_data)
balance = income - expenses


# -------------------- Dashboard --------------------

if page == "Dashboard":
    st.header("Financial Overview")
    st.caption(today.strftime("%B %Y"))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Income", money(income))
    col2.metric("Total Expenses", money(expenses))
    col3.metric("Net Balance", money(balance))
    col4.metric(
        "Transactions",
        len(current_data)
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Expenses by Category")

        category_data = current_data[
            current_data["transaction_type"] == "Expense"
        ]

        if not category_data.empty:
            grouped = category_data.groupby(
                "category", as_index=False
            )["amount"].sum()

            fig = px.pie(
                grouped,
                names="category",
                values="amount",
                hole=0.45,
                title="Current Month Spending",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add expenses to view your category chart.")

    with right:
        st.subheader("Income vs Expenses")

        comparison = pd.DataFrame({
            "Type": ["Income", "Expenses"],
            "Amount": [income, expenses],
        })

        fig = px.bar(
            comparison,
            x="Type",
            y="Amount",
            text_auto=".2s",
            title="Current Month Summary",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Budget Status")

    budgets = get_budgets(current_month)
    if budgets:
        for budget in budgets:
            spent = current_data.loc[
                (current_data["transaction_type"] == "Expense")
                & (current_data["category"] == budget["category"]),
                "amount",
            ].sum()

            limit = float(budget["amount"])
            ratio = float(spent) / limit
            st.write(
                f"**{budget['category']}** — "
                f"{money(spent)} of {money(limit)}"
            )
            st.progress(min(ratio, 1.0))

            if ratio > 1:
                st.error("Budget exceeded!")
            elif ratio >= 0.8:
                st.warning("You have used at least 80% of this budget.")
            else:
                st.success("Within budget.")
    else:
        st.info("Set a budget in the Budget Planner page.")

    st.subheader("Recent Transactions")
    if not df.empty:
        recent = df.head(5).copy()
        recent["date"] = recent["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            recent[
                ["date", "transaction_type", "category",
                 "amount", "description"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No transactions yet. Add your first transaction.")


# -------------------- Add Transaction --------------------

elif page == "Add Transaction":
    st.header("Add a Transaction")

    with st.form("add_transaction_form", clear_on_submit=True):
        transaction_type = st.selectbox(
            "Transaction Type", ["Expense", "Income"]
        )

        if transaction_type == "Income":
            income_categories = [
                "Salary", "Freelance", "Other"
            ]
            category = st.selectbox(
                "Category", income_categories
            )
        else:
            expense_categories = [
                c for c in CATEGORIES
                if c not in ["Salary", "Freelance"]
            ]
            category = st.selectbox(
                "Category", expense_categories
            )

        transaction_date = st.date_input(
            "Date", value=date.today()
        )
        amount = st.number_input(
            "Amount (₹)", min_value=0.01,
            value=100.0, step=50.0
        )
        description = st.text_input(
            "Description", max_chars=200,
            placeholder="e.g. Lunch, bus fare, monthly salary"
        )

        submitted = st.form_submit_button(
            "Save Transaction", type="primary"
        )

    if submitted:
        if amount <= 0:
            st.error("Amount must be greater than zero.")
        else:
            add_transaction(
                transaction_date.isoformat(),
                transaction_type,
                category,
                float(amount),
                description,
            )
            st.success("Transaction saved successfully!")
            st.rerun()


# -------------------- Manage Transactions --------------------

elif page == "Manage Transactions":
    st.header("Manage Transactions")

    if df.empty:
        st.info("There are no transactions to manage.")
    else:
        filter_type = st.selectbox(
            "Filter by type",
            ["All", "Income", "Expense"]
        )
        search_text = st.text_input(
            "Search category or description"
        )

        filtered = df.copy()

        if filter_type != "All":
            filtered = filtered[
                filtered["transaction_type"] == filter_type
            ]

        if search_text.strip():
            term = search_text.strip()
            matches = (
                filtered["category"].str.contains(
                    term, case=False, na=False
                )
                | filtered["description"].str.contains(
                    term, case=False, na=False
                )
            )
            filtered = filtered[matches]

        display_df = filtered.copy()
        display_df["date"] = display_df["date"].dt.strftime(
            "%Y-%m-%d"
        )

        st.dataframe(
            display_df[
                ["id", "date", "transaction_type",
                 "category", "amount", "description"]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("Edit or Delete a Transaction")

        if not filtered.empty:
            transaction_ids = filtered["id"].astype(int).tolist()

            selected_id = st.selectbox(
                "Choose transaction ID",
                transaction_ids,
                format_func=lambda x: (
                    f"ID {x} — "
                    f"{filtered.loc[filtered['id'] == x, 'category'].iloc[0]}"
                    f" — ₹{filtered.loc[filtered['id'] == x, 'amount'].iloc[0]:,.2f}"
                ),
            )

            record = next(
                row for row in transactions
                if row["id"] == selected_id
            )

            with st.form("edit_transaction_form"):
                edit_type = st.selectbox(
                    "Type",
                    ["Expense", "Income"],
                    index=["Expense", "Income"].index(
                        record["transaction_type"]
                    ),
                )

                allowed_categories = (
                    ["Salary", "Freelance", "Other"]
                    if edit_type == "Income"
                    else [
                        c for c in CATEGORIES
                        if c not in ["Salary", "Freelance"]
                    ]
                )

                old_category = record["category"]
                if old_category not in allowed_categories:
                    old_category = allowed_categories[0]

                edit_category = st.selectbox(
                    "Category",
                    allowed_categories,
                    index=allowed_categories.index(old_category),
                )
                edit_date = st.date_input(
                    "Date",
                    value=date.fromisoformat(record["date"]),
                )
                edit_amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.01,
                    value=float(record["amount"]),
                    step=50.0,
                    key=f"edit_amount_{selected_id}",
                )
                edit_description = st.text_input(
                    "Description",
                    value=record["description"],
                    max_chars=200,
                )

                update_clicked = st.form_submit_button(
                    "Update Transaction"
                )

            if update_clicked:
                update_transaction(
                    selected_id,
                    edit_date.isoformat(),
                    edit_type,
                    edit_category,
                    float(edit_amount),
                    edit_description,
                )
                st.success("Transaction updated.")
                st.rerun()

            if st.button(
                "Delete Selected Transaction",
                type="secondary",
            ):
                st.session_state["confirm_delete_id"] = selected_id

            if st.session_state.get("confirm_delete_id") == selected_id:
                st.warning(
                    f"Delete transaction ID {selected_id}? "
                    "This action cannot be undone."
                )
                confirm_col, cancel_col = st.columns(2)

                if confirm_col.button(
                    "Confirm Delete", type="primary"
                ):
                    delete_transaction(selected_id)
                    st.session_state.pop("confirm_delete_id", None)
                    st.success("Transaction deleted.")
                    st.rerun()

                if cancel_col.button("Cancel Delete"):
                    st.session_state.pop("confirm_delete_id", None)
                    st.rerun()


# -------------------- Budget Planner --------------------

elif page == "Budget Planner":
    st.header("Monthly Budget Planner")

    with st.form("budget_form"):
        budget_month = st.date_input(
            "Choose month",
            value=date(today.year, today.month, 1),
        )
        budget_category = st.selectbox(
            "Expense Category",
            [
                c for c in CATEGORIES
                if c not in ["Salary", "Freelance"]
            ],
        )
        budget_amount = st.number_input(
            "Monthly Limit (₹)",
            min_value=0.01,
            value=5000.0,
            step=500.0,
        )
        budget_submitted = st.form_submit_button(
            "Save Budget"
        )

    if budget_submitted:
        save_budget(
            budget_month.strftime("%Y-%m"),
            budget_category,
            float(budget_amount),
        )
        st.success("Budget saved or updated.")
        st.rerun()

    selected_month = st.selectbox(
        "View budgets for",
        options=[
            date(y, m, 1).strftime("%Y-%m")
            for y, m in [
                (today.year, today.month),
                (today.year - 1, today.month),
                (today.year, today.month - 1 or 12),
            ]
        ],
        index=0,
    )

    # Use the current date picker month by default for the report below.
    budgets = get_budgets(selected_month)
    budget_expenses = month_data(selected_month)

    if budgets:
        for budget in budgets:
            spent = budget_expenses.loc[
                (budget_expenses["transaction_type"] == "Expense")
                & (budget_expenses["category"] == budget["category"]),
                "amount",
            ].sum()

            limit = float(budget["amount"])
            remaining = limit - float(spent)

            st.write(
                f"**{budget['category']}** — "
                f"Spent {money(spent)} / Budget {money(limit)}"
            )
            st.progress(min(float(spent) / limit, 1.0))

            if remaining < 0:
                st.error(f"Over budget by {money(abs(remaining))}.")
            else:
                st.caption(f"Remaining: {money(remaining)}")

        st.divider()
        budget_df = pd.DataFrame(budgets)
        st.dataframe(
            budget_df[["month", "category", "amount"]],
            use_container_width=True,
            hide_index=True,
        )

        delete_id = st.selectbox(
            "Budget to delete",
            [b["id"] for b in budgets],
            format_func=lambda x: next(
                f"{b['category']} — ₹{b['amount']:,.2f}"
                for b in budgets if b["id"] == x
            ),
        )

        if st.button("Delete Selected Budget"):
            delete_budget(delete_id)
            st.success("Budget deleted.")
            st.rerun()
    else:
        st.info("No budgets for this month yet.")


# -------------------- Reports and Insights --------------------

elif page == "Reports & Insights":
    st.header("Reports & Spending Insights")

    if df.empty:
        st.info("Add transactions to generate reports.")
    else:
        report_start = st.date_input(
            "Start date",
            value=date(today.year, today.month, 1),
            key="report_start",
        )
        report_end = st.date_input(
            "End date",
            value=today,
            key="report_end",
        )

        if report_start > report_end:
            st.error("Start date must not be after end date.")
        else:
            report_df = df[
                (df["date"].dt.date >= report_start)
                & (df["date"].dt.date <= report_end)
            ].copy()

            report_income, report_expenses = calculate_totals(
                report_df
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Income", money(report_income))
            col2.metric("Expenses", money(report_expenses))
            col3.metric(
                "Net Balance",
                money(report_income - report_expenses),
            )

            expense_df = report_df[
                report_df["transaction_type"] == "Expense"
            ].copy()

            if not expense_df.empty:
                st.subheader("Category Analysis")

                category_summary = expense_df.groupby(
                    "category", as_index=False
                )["amount"].sum().sort_values(
                    "amount", ascending=False
                )

                st.plotly_chart(
                    px.bar(
                        category_summary,
                        x="category",
                        y="amount",
                        title="Expenses by Category",
                    ),
                    use_container_width=True,
                )

                top = category_summary.iloc[0]
                st.info(
                    f"Your highest-spending category is "
                    f"**{top['category']}** at {money(top['amount'])}."
                )

                st.subheader("Monthly Expense Trend")

                expense_df["month"] = (
                    expense_df["date"].dt.to_period("M").astype(str)
                )
                monthly = expense_df.groupby(
                    "month", as_index=False
                )["amount"].sum()

                st.plotly_chart(
                    px.line(
                        monthly,
                        x="month",
                        y="amount",
                        markers=True,
                        title="Monthly Spending",
                    ),
                    use_container_width=True,
                )

            st.subheader("Download Report")

            export_df = report_df.copy()
            export_df["date"] = export_df["date"].dt.strftime(
                "%Y-%m-%d"
            )
            csv = export_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                "Download Transactions as CSV",
                data=csv,
                file_name="expense_report.csv",
                mime="text/csv",
            )

            st.caption(
                "Insights are based only on the transactions "
                "recorded in this application."
            )
