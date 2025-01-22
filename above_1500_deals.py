import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

def show_above_1500_clients():
    st.title("Clients with Budget above 1500$ less than 200$")

    db_params = {
        'dbname': st.secrets["database"]["DB_NAME"],
        'user': st.secrets["database"]["DB_USER"],
        'password': st.secrets["database"]["DB_PASSWORD"],
        'host': st.secrets["database"]["DB_HOST"],
        'port': st.secrets["database"]["DB_PORT"]
    }

    # Date input to select a start and end date
    st.subheader("Select Date Range for Client Records")
    start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=1))
    end_date = st.date_input("End Date", datetime.now().date())

    # Convert dates to datetime format with start and end of the day
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Query to fetch clients with specified conditions
    fetch_clients_query = f"""
        SELECT DISTINCT ON (c.id)
            c.id AS client_id,
            c.fullname AS client_name,
            CONCAT('https://services.followupboss.com/2/people/view/', c.id) AS followup_boss_link,
            e.fullname AS employee_name,
            r.budget,
            r.beds,
            r.move_in_date AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS move_in_date,
            r.credit_score,
            r.section8,
            c.created AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS created_at,
            c.assigned_employee,
            c.addresses->0->>'city' AS originating_city,
            c.addresses->0->>'state' AS originating_state
        FROM 
            public.client c
        LEFT JOIN 
            public.employee e ON c.assigned_employee = e.id
        LEFT JOIN 
            public.requirements r ON c.id = r.client_id
        WHERE 
            r.budget > 1500 AND r.budget < 2000
            AND c.created >= '{start_datetime}'::timestamp AT TIME ZONE 'CST'
            AND c.created <= '{end_datetime}'::timestamp AT TIME ZONE 'CST'
        ORDER BY 
            c.id, c.created;
    """

    def fetch_data(query):
        connection = None
        cursor = None
        try:
            connection = psycopg2.connect(**db_params)
            cursor = connection.cursor()
            cursor.execute(query)
            records = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(records, columns=column_names)
            return df
        except Exception as error:
            st.error(f"Error fetching records: {error}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def display_clients_as_table(df):
        st.subheader("Filtered Clients (Budget < 1500 & Budget > 2000)")
        
        if df.empty:
            st.write("No clients found.")
        else:
            total_clients = len(df)
            not_assigned_to_317_318_319 = (~df['assigned_employee'].isin([317, 318, 319,410,415,416])).sum()
            percentage_not_assigned = (not_assigned_to_317_318_319 / total_clients) * 100

            st.subheader(f"Percentage of clients assigned to employees: {percentage_not_assigned:.2f}%")

            df['FUB Link'] = df.apply(lambda row: f'<a href="{row["followup_boss_link"]}" target="_blank">Go to Link</a>', axis=1)
            df = df[['client_name', 'employee_name', 'budget', 'beds', 'move_in_date', 'credit_score', 'section8', 'created_at', 'originating_city', 'originating_state', 'FUB Link']]

            st.write(df.to_html(escape=False), unsafe_allow_html=True)

    clients_data = fetch_data(fetch_clients_query)

    display_clients_as_table(clients_data)
