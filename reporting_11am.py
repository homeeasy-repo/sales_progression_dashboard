import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

def generate_11am_report():
    st.title("11 AM Report")

    db_params = {
        'dbname': st.secrets["database"]["DB_NAME"],
        'user': st.secrets["database"]["DB_USER"],
        'password': st.secrets["database"]["DB_PASSWORD"],
        'host': st.secrets["database"]["DB_HOST"],
        'port': st.secrets["database"]["DB_PORT"]
    }

    # Date input to select a start and end date
    st.subheader("Select Date Range for the Report")
    start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=1))
    end_date = st.date_input("End Date", datetime.now().date())

    # Convert dates to datetime format with start and end of the day
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Query to fetch client data
    fetch_clients_query = f"""
    WITH clients_created_today AS (
        SELECT 
            c.id AS client_id,
            c.fullname AS client_name,
            e.fullname AS employee_name,
            c.created AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS created_at,
            r.beds AS bedrooms,
            r.baths AS bathrooms,
            r.move_in_date AT TIME ZONE 'UTC' AT TIME ZONE 'CST' AS move_in_date,
            r.budget AS budget,
            CONCAT('https://services.followupboss.com/2/people/view/', c.id) AS fub_link,
            (
                SELECT COUNT(*) 
                FROM public.textmessage tm
                WHERE tm.client_id = c.id 
                  AND tm.employee_id = e.id
                  AND tm.is_incoming = FALSE -- Only include messages sent by the employee
            ) AS total_employee_messages
        FROM 
            public.client c
        LEFT JOIN 
            public.employee e ON c.assigned_employee = e.id
        LEFT JOIN 
            public.requirements r ON c.id = r.client_id
        WHERE 
            c.created >= '{start_datetime}'::timestamp AT TIME ZONE 'CST'
            AND c.created <= '{end_datetime}'::timestamp AT TIME ZONE 'CST'
            AND (c.assigned_employee NOT IN (317, 318, 319, 344) OR c.assigned_employee IS NULL)
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
        c.employee_name,
        c.created_at,
        c.bedrooms,
        c.bathrooms,
        c.move_in_date,
        c.budget,
        c.fub_link,
        c.total_employee_messages, -- Correct column reference
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM public.call cl
                WHERE cl.client_id = c.client_id
            ) THEN 'YES'
            ELSE 'NO'
        END AS call_status
    FROM 
        clients_created_today c
    LEFT JOIN 
        clients_with_received_status r ON c.client_id = r.client_id
    ORDER BY 
        c.created_at DESC;
    """
    fetch_employee_summary_query = f"""
        SELECT 
            e.fullname AS employee_name,
            COUNT(c.id) AS number_of_clients,
            COALESCE(SUM(
                (
                    SELECT COUNT(*) 
                    FROM public.textmessage tm
                    WHERE tm.employee_id = e.id 
                      AND tm.client_id = c.id
                      AND tm.is_incoming = FALSE
                )
            ), 0) AS total_employee_messages
        FROM 
            public.client c
        LEFT JOIN 
            public.employee e ON c.assigned_employee = e.id
        WHERE 
            c.created >= '{start_datetime}'::timestamp AT TIME ZONE 'CST'
            AND c.created <= '{end_datetime}'::timestamp AT TIME ZONE 'CST'
            AND (c.assigned_employee NOT IN (317, 318, 319, 344) OR c.assigned_employee IS NULL)
        GROUP BY 
            e.fullname
        ORDER BY 
            number_of_clients DESC;
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
            return pd.DataFrame(records, columns=column_names)
        except Exception as error:
            st.error(f"Error fetching records: {error}")
            return pd.DataFrame()
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    # Fetch the data
    client_data = fetch_data(fetch_clients_query)
    employee_summary_data = fetch_data(fetch_employee_summary_query)

    # Display the clients table
    st.subheader("Client Details")
    if not client_data.empty:
        client_data['FUB Link'] = client_data.apply(
            lambda row: f'<a href="{row["fub_link"]}" target="_blank">Go to Link</a>', axis=1
        )
        client_data_display = client_data[['client_name', 'employee_name', 'created_at', 'bedrooms', 
                                   'bathrooms', 'move_in_date', 'budget', 'total_employee_messages', 'call_status', 'FUB Link']]

        st.write(client_data_display.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Add option to download as CSV
        csv = client_data_display.to_csv(index=False)
        st.download_button(label="Download 11AM Reporting CSV File", data=csv, file_name="11AM Reporting.csv", mime="text/csv")
    else:
        st.write("No clients found in the selected date range.")

    # Display the employee summary table
    st.subheader("Employee Summary")
    if not employee_summary_data.empty:
        st.dataframe(employee_summary_data, use_container_width=True)
    else:
        st.write("No leads assigned to employees in the selected date range.")

