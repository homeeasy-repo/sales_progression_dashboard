import streamlit as st
import psycopg2
import pandas as pd

def show_recent_clients():
    st.title("Clients Created in Last 24 Hours (Assigned to Employees 317, 318, 319,410,415,416,160, 20)")

    db_params = {
        'dbname': st.secrets["database"]["DB_NAME"],
        'user': st.secrets["database"]["DB_USER"],
        'password': st.secrets["database"]["DB_PASSWORD"],
        'host': st.secrets["database"]["DB_HOST"],
        'port': st.secrets["database"]["DB_PORT"]
    }

    # Query to fetch clients created in the last 24 hours and assigned to employees 317, 318, 319
    fetch_clients_query = """
        SELECT 
            c.id AS client_id,
            c.fullname AS client_name,
            e.fullname AS employee_name,
            CONCAT('https://services.followupboss.com/2/people/view/', c.id) AS followup_boss_link
        FROM 
            public.client c
        JOIN 
            public.employee e ON c.assigned_employee = e.id
        WHERE 
            c.created >= NOW() - INTERVAL '24 hours'
            AND e.id IN (317, 318, 319,410,415,416,160, 20)
        ORDER BY 
            c.id;
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
        st.subheader("Recent Clients (Last 24 Hours)")
        if df.empty:
            st.write("No clients found.")
        else:
            # Create the DataFrame with clickable links
            df['FUB Link'] = df.apply(lambda row: f'<a href="{row["followup_boss_link"]}" target="_blank">Go to Link</a>', axis=1)
            df = df[['client_name', 'employee_name', 'FUB Link']]

            # Render the DataFrame as an HTML table
            st.write(df.to_html(escape=False), unsafe_allow_html=True)

    # Fetch clients
    clients_data = fetch_data(fetch_clients_query)

    # Display clients in a table with clickable FUB links
    display_clients_as_table(clients_data)

