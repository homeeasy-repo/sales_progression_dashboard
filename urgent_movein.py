import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

def show_clients_with_urgent_movein():
    st.title("Responsive Clients")

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

    # Define the current date and thresholds for move-in dates
    current_date = pd.Timestamp(datetime.now().date())  # Convert current_date to Timestamp
    thirty_days_later = current_date + pd.Timedelta(days=30)
    sixty_days_later = current_date + pd.Timedelta(days=60)

    # Updated query to fetch responsive clients with beds, baths, "Calls" column, and move-in filters
    fetch_responsive_clients_query = f"""
    WITH clients_created_today AS (
        SELECT 
            c.id AS client_id,
            c.stage_id AS current_stage,
            e.fullname AS assigned_employee_name,
            c.fphone1 AS phone_number,
            c.fullname AS client_name,
            r.move_in_date AS move_in_date,
            r.budget AS budget,
            r.beds AS beds,
            r.baths AS baths,
            r.section8 AS section_8,
            r.credit_score AS credit_score,
            (c.addresses->0->>'city') AS city,
            (c.addresses->0->>'state') AS state,
            (c.addresses->0->>'street') AS street
        FROM 
            public.client c
        LEFT JOIN 
            public.requirements r ON c.id = r.client_id
        LEFT JOIN 
            public.employee e ON c.assigned_employee = e.id
        WHERE 
            c.created >= '{start_datetime}'::timestamp AT TIME ZONE 'CST'
            AND c.created <= '{end_datetime}'::timestamp AT TIME ZONE 'CST'
    ),
    clients_with_received_status AS (
        SELECT DISTINCT 
            tm.client_id
        FROM 
            public.textmessage tm
        WHERE 
            tm.status = 'Received'
    )
    SELECT 
        c.client_id,
        c.client_name,
        CONCAT('https://services.followupboss.com/2/people/view/', c.client_id) AS followup_boss_link,
        c.assigned_employee_name AS employee_name,
        c.phone_number,
        c.budget,
        c.beds,
        c.baths,
        c.move_in_date,
        c.credit_score,
        c.section_8 AS section8,
        c.city,
        c.state,
        c.street,
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM public.call cl
                WHERE cl.client_id = c.client_id
            ) THEN 'True'
            ELSE 'False'
        END AS calls
    FROM 
        clients_created_today c
    INNER JOIN 
        clients_with_received_status r ON c.client_id = r.client_id
    WHERE 
        c.move_in_date IS NOT NULL
    ORDER BY 
        c.move_in_date ASC;
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

    def display_clients_as_table(title, df):
        st.subheader(title)
        
        if df.empty:
            st.write(f"No clients found for {title}.")
        else:
            df['FUB Link'] = df.apply(
                lambda row: f'<a href="{row["followup_boss_link"]}" target="_blank">Go to Link</a>', axis=1
            )
            df = df[['client_name', 'employee_name', 'phone_number', 'budget', 'beds', 'baths', 
                     'move_in_date', 'credit_score', 'section8', 'city', 'state', 'street', 'calls', 'FUB Link']]
            
            st.write(df.to_html(escape=False), unsafe_allow_html=True)

    # Fetch the data
    responsive_clients_data = fetch_data(fetch_responsive_clients_query)

    # Filter for ASAP move-in (within 30 days)
    if responsive_clients_data is not None:
        asap_movein_clients = responsive_clients_data[
            (pd.to_datetime(responsive_clients_data['move_in_date']) >= current_date) &
            (pd.to_datetime(responsive_clients_data['move_in_date']) < thirty_days_later)
        ]

        # Filter for move-in between 30 and 60 days
        thirty_to_sixty_days_clients = responsive_clients_data[
            (pd.to_datetime(responsive_clients_data['move_in_date']) >= thirty_days_later) &
            (pd.to_datetime(responsive_clients_data['move_in_date']) <= sixty_days_later)
        ]

        # Display the tables
        display_clients_as_table("ASAP Move-In Clients (Within 30 Days)", asap_movein_clients)
        display_clients_as_table("Move-In Clients (30 to 60 Days)", thirty_to_sixty_days_clients)
