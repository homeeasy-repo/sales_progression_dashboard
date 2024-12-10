import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

def show_clients_with_urgent_movein():
    st.title("Clients with Urgent Move-In Dates (Within 60 Days)")

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

    # Define the current date and the 60-day threshold for move-in
    current_date = datetime.now().date()
    sixty_days_later = current_date + timedelta(days=60)

    # Updated query to fetch clients with move-in dates within 60 days, creation date filter, and "Calls" check
    fetch_urgent_clients_query = f"""
        SELECT DISTINCT ON (c.id)
            c.id AS client_id,
            c.fullname AS client_name,
            CONCAT('https://services.followupboss.com/2/people/view/', c.id) AS followup_boss_link,
            e.fullname AS employee_name,
            r.budget,
            r.beds,
            r.baths,
            r.move_in_date AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS move_in_date,
            r.credit_score,
            r.section8,
            c.created AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS created_at,
            c.addresses->0->>'city' AS originating_city,
            c.addresses->0->>'state' AS originating_state,
            CASE 
                WHEN EXISTS (
                    SELECT 1 
                    FROM public.call cl
                    WHERE cl.client_id = c.id
                ) THEN 'True'
                ELSE 'False'
            END AS calls
        FROM 
            public.client c
        LEFT JOIN 
            public.employee e ON c.assigned_employee = e.id
        LEFT JOIN 
            public.requirements r ON c.id = r.client_id
        WHERE 
            r.move_in_date >= '{current_date}'::date
            AND r.move_in_date <= '{sixty_days_later}'::date
            AND c.created >= '{start_datetime}'::timestamp AT TIME ZONE 'CST'
            AND c.created <= '{end_datetime}'::timestamp AT TIME ZONE 'CST'
        ORDER BY 
            c.id, r.move_in_date ASC;
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
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def display_clients_as_table(df):
        st.subheader("Clients with Move-In Dates Within 60 Days")
        
        if df is None or df.empty:
            st.write("No clients found with urgent move-in dates.")
        else:
            df['FUB Link'] = df.apply(
                lambda row: f'<a href="{row["followup_boss_link"]}" target="_blank">Go to Link</a>', axis=1
            )
            df = df[['client_name', 'employee_name', 'budget', 'beds', 'baths', 
                     'move_in_date', 'credit_score', 'section8', 'originating_city', 
                     'originating_state', 'calls', 'FUB Link']]
            
            st.write(df.to_html(escape=False), unsafe_allow_html=True)

    # Fetch and display the data
    urgent_clients_data = fetch_data(fetch_urgent_clients_query)
    display_clients_as_table(urgent_clients_data)


# show_clients_with_urgent_movein()