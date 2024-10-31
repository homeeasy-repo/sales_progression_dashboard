import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

def may_update_channel_clients():
    st.title("Buildings Sent to Clients")

    # Database connection parameters
    db_params = {
        'dbname': st.secrets["database"]["DB_NAME"],
        'user': st.secrets["database"]["DB_USER"],
        'password': st.secrets["database"]["DB_PASSWORD"],
        'host': st.secrets["database"]["DB_HOST"],
        'port': st.secrets["database"]["DB_PORT"]
    }

    selected_date = st.date_input("Select a date to view clients", datetime.now().date())

    selected_datetime_start = f"{selected_date} 00:00:00"
    selected_datetime_end = f"{selected_date} 23:59:59"

    fetch_clients_query = f"""
        SELECT DISTINCT ON (c.id)
            c.id AS client_id,
            c.fullname AS client_name,
            CONCAT('https://services.followupboss.com/2/people/view/', c.id) AS followup_boss_link,
            e.fullname AS employee_name,
            r.budget,
            r.beds,
            r.move_in_date AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS move_in_date_ct,
            r.credit_score,
            r.section8,
            c.created AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS created_ct
        FROM 
            public.client c
        JOIN 
            public.client_prop_matching cp ON c.id = cp.client_id
        LEFT JOIN 
            public.employee e ON c.assigned_employee = e.id
        LEFT JOIN 
            public.requirements r ON c.id = r.client_id
        WHERE 
            c.created >= '{selected_datetime_start}'::timestamp AT TIME ZONE 'CST'
            AND c.created <= '{selected_datetime_end}'::timestamp AT TIME ZONE 'CST'
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
        st.subheader(f"Clients on {selected_date}")
        if df.empty:
            st.write("No clients found.")
        else:
            df['FUB Link'] = df.apply(lambda row: f'<a href="{row["followup_boss_link"]}" target="_blank">Go to Link</a>', axis=1)
            df = df[['client_name', 'employee_name', 'budget', 'beds', 'move_in_date_ct', 'credit_score', 'section8', 'created_ct', 'FUB Link']]

            st.write(df.to_html(escape=False), unsafe_allow_html=True)

    clients_data = fetch_data(fetch_clients_query)

    display_clients_as_table(clients_data)

may_update_channel_clients()
