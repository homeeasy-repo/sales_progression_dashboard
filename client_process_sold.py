import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

def show_responsive_clients():
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

    # Query for all clients
    fetch_all_clients_query = f"""
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
            AND (c.assigned_employee NOT IN (317, 318, 319,410,415,416,344) OR c.assigned_employee IS NULL)
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
        ROW_NUMBER() OVER (ORDER BY c.client_id) AS count,
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
            ) THEN 'YES'
            ELSE 'NO'
        END AS calls
    FROM 
        clients_created_today c
    INNER JOIN 
        clients_with_received_status r ON c.client_id = r.client_id
    ORDER BY 
        c.client_id;
    """

    # Query for clients assigned to employees 317, 318, and 319
    fetch_specific_employees_query = f"""
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
            AND c.assigned_employee IN (317, 318, 319,410,415,416)
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
        ROW_NUMBER() OVER (ORDER BY c.client_id) AS count,
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
            ) THEN 'YES'
            ELSE 'NO'
        END AS calls
    FROM 
        clients_created_today c
    INNER JOIN 
        clients_with_received_status r ON c.client_id = r.client_id
    ORDER BY 
        c.client_id;
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

    def display_clients_as_table(df, title):
        st.subheader(title)
        
        if df is None or df.empty:
            st.write(f"No clients found for {title}.")
        else:
            df['FUB Link'] = df.apply(
                lambda row: f'<a href="{row["followup_boss_link"]}" target="_blank">Go to Link</a>', axis=1
            )
            df_display = df[['count', 'client_name', 'employee_name', 'phone_number', 'budget', 'beds', 'baths', 
                             'move_in_date', 'credit_score', 'section8', 'city', 'state', 'street', 'calls', 'FUB Link']]
            st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

            # Add download button for CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label=f"Download {title} as CSV",
                data=csv,
                file_name=f"{title.replace(' ', '_').lower()}.csv",
                mime="text/csv"
            )

    # Fetch and display data for all clients
    all_clients_data = fetch_data(fetch_all_clients_query)
    display_clients_as_table(all_clients_data, "All Clients (Assigned to Sales Rep)")

    # Fetch and display data for specific employees
    specific_employees_data = fetch_data(fetch_specific_employees_query)
    display_clients_as_table(specific_employees_data, "All Clients Assigned to May Account's")

