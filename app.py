import calendar  # Core Python Module
from datetime import datetime  # Core Python Module

import plotly.graph_objects as go  # pip install plotly
import streamlit as st  # pip install streamlit
from streamlit_option_menu import option_menu  # pip install streamlit-option-menu

import streamlit_authenticator as stauth # pip install streamlit-authenticator
import database as db  # local import

# -------------- SETTINGS --------------
incomes = ["Salary", "Other Income"]
expenses = ["Rent", "Utilities", "Groceries", "Car", "Other Expenses", "Saving"]
currency = "USD"
page_title = "Income and Expense Tracker"
page_icon = ":money_with_wings:"  # emojis: https://www.webfx.com/tools/emoji-cheat-sheet/
layout = "centered"
# --------------------------------------

st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
st.title(page_title + " " + page_icon)


# --- AUTHENTICATION SETTINGS ---
import yaml
from yaml.loader import SafeLoader
with open('./.streamlit/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

name, authentication_status, username = authenticator.login('Login', 'main')


# --- DROP DOWN VALUES FOR SELECTING THE PERIOD ---
years = [datetime.today().year, datetime.today().year + 1]
months = list(calendar.month_name[1:])

# --- DATABASE INTERFACE ---
def get_all_periods():
    items = db.fetch_all_periods()
    periods = [item["key"] for item in items]
    return periods


if st.session_state["authentication_status"]:
    authenticator.logout('Logout', 'main')

    # --- NAVIGATION MENU ---
    selected = option_menu(
        menu_title=None,
        options=["Data Entry", "Data Visualization"],
        icons=["pencil-fill", "bar-chart-fill"],  # https://icons.getbootstrap.com/
        orientation="horizontal",
    )
    
    # --- INPUT & SAVE PERIODS ---
    if selected == "Data Entry":
        st.header(f"Data Entry in {currency}")
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            col1.selectbox("Select Month:", months, key="month")
            col2.selectbox("Select Year:", years, key="year")

            "---"
            with st.expander("Income"):
                for income in incomes:
                    st.number_input(f"{income}:", min_value=0, format="%i", step=10, key=income)
            with st.expander("Expenses"):
                for expense in expenses:
                    st.number_input(f"{expense}:", min_value=0, format="%i", step=10, key=expense)
            with st.expander("Comment"):
                comment = st.text_area("", placeholder="Enter a comment here ...")

            "---"
            submitted = st.form_submit_button("Save Data")
            if submitted:
                # Calculate total income and total expenses
                total_income = sum(st.session_state[income] for income in incomes)
                total_expenses = sum(st.session_state[expense] for expense in expenses)

                # Check if total income is equal to or exceeds total expenses
                if total_income >= total_expenses:
                    period = str(st.session_state["year"]) + "_" + str(st.session_state["month"])

                    if period in get_all_periods():
                        st.error("This period already exists. Please select another period.")
                    else:
                        incomes = {income: st.session_state[income] for income in incomes}
                        expenses = {expense: st.session_state[expense] for expense in expenses}
                        db.insert_period(period, incomes, expenses, comment)
                        st.success("Data saved!")
                else:
                    st.error("Total income must equal or exceed total expenses. Please adjust your entries.")


        st.header("Data History")

        # Allow users to edit and save data
        with st.expander("Edit Data"):
            selected_period = st.selectbox("Select Period:", get_all_periods())
            selected_data = db.get_period(selected_period)

            if selected_data:
                st.write(f"Editing data for {selected_period}")
                with st.form("edit_form"):
                    # Display the selected data for editing
                    st.write("Edit Income:")
                    edited_incomes = {}
                    for income, value in selected_data["incomes"].items():
                        edited_income = st.number_input(income, min_value=0, format="%i", step=10, value=value)
                        edited_incomes[income] = edited_income

                    st.write("Edit Expenses:")
                    edited_expenses = {}
                    for expense, value in selected_data["expenses"].items():
                        edited_expense = st.number_input(expense, min_value=0, format="%i", step=10, value=value)
                        edited_expenses[expense] = edited_expense

                    edited_comment = st.text_area("Edit Comment:", value=selected_data["comment"])

                    if st.form_submit_button("Save Changes"):
                        # Calculate total income and total expenses
                        total_income = sum(edited_incomes.values())
                        total_expenses = sum(edited_expenses.values())

                        # Check if total income is equal to or exceeds total expenses
                        if total_income >= total_expenses:
                            db.update_period(selected_period, edited_incomes, edited_expenses, edited_comment)
                            st.success("Data updated!")
                        else:
                            st.error("Total income must equal or exceed total expenses. Please adjust your entries.")  
    # --- PLOT PERIODS ---
    if selected == "Data Visualization":
        st.header("Data Visualization")
        with st.form("saved_periods"):
            period = st.selectbox("Select Period:", get_all_periods())
            submitted = st.form_submit_button("Plot Period")
            if submitted:
                # Get data from database
                period_data = db.get_period(period)
                comment = period_data.get("comment")
                expenses = period_data.get("expenses")
                incomes = period_data.get("incomes")

                # Create metrics
                total_income = sum(incomes.values())
                total_expense = sum(expenses.values())
                remaining_budget = total_income - total_expense
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Income", f"{total_income} {currency}")
                col2.metric("Total Expense", f"{total_expense} {currency}")
                col3.metric("Remaining Budget", f"{remaining_budget} {currency}")
                st.text(f"Comment: {comment}")

                # Create sankey chart
                label = list(incomes.keys()) + ["Total Income"] + list(expenses.keys())
                source = list(range(len(incomes))) + [len(incomes)] * len(expenses)
                target = [len(incomes)] * len(incomes) + [label.index(expense) for expense in expenses.keys()]
                value = list(incomes.values()) + list(expenses.values())

                node_colors = ["#1f77b4"] * len(incomes) + ["#ff7f0e"] + ["#d62728"] * len(expenses)

                # Data to dict, dict to sankey
                link = dict(source=source, target=target, value=value)
                node = dict(label=label, pad=20, thickness=30, color=node_colors)
                data = go.Sankey(link=link, node=node)

                # Plot it!
                fig = go.Figure(data)
                fig.update_layout(margin=dict(l=0, r=0, t=5, b=5))
                st.plotly_chart(fig, use_container_width=True)
            


        st.header("Trending Earnings and Expenses")

        # Fetch all saved periods from the database
        periods = db.fetch_all_periods()

        # Extract data for plotting
        months = []
        total_incomes = []
        total_expenses = []

        for period_data in periods:
            period = period_data["key"]
            incomes = period_data["incomes"]
            expenses = period_data["expenses"]

            # Calculate total income and total expense for each period
            total_income = sum(incomes.values())
            total_expense = sum(expenses.values())

            months.append(period)
            total_incomes.append(total_income)
            total_expenses.append(total_expense)

        # Create a line chart
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=months, y=total_incomes, mode="lines+markers", name="Total Income"))
        fig.add_trace(go.Scatter(x=months, y=total_expenses, mode="lines+markers", name="Total Expense"))

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Amount",
            title="Trending Earnings and Expenses",
        )

        st.plotly_chart(fig, use_container_width=True)

elif st.session_state["authentication_status"] == False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] == None:
    st.warning('Please enter your username and password')



