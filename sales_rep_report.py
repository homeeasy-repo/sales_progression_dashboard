import os
import psycopg2
import pandas as pd
import json
import streamlit as st

from datetime import datetime, timedelta

ASSIGNED_MINUTES = 480
SECONDS_PER_MESSAGE = 5

db_params = {
    'dbname': st.secrets["database"]["DB_NAME"],
    'user': st.secrets["database"]["DB_USER"],
    'password': st.secrets["database"]["DB_PASSWORD"],
    'host': st.secrets["database"]["DB_HOST"],
    'port': st.secrets["database"]["DB_PORT"]
}

employee_names = ['Mukund Chopra','John Green', 'Sara Edward','Ryan Rehman','Omar Blake','Simon Sinek','Daniel Robinson', 'Moohi Ahmed','Waseem Zubair','Alina Victor']

end_time = datetime.now()
start_time = end_time - timedelta(days=1)
start_time = start_time.replace(hour=13, minute=0, second=0)
end_time = start_time + timedelta(hours=12)
start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
print(f"Start time: {start_time_str}")
print(f"End time: {end_time_str}")

fetch_client_ids_query = """
SELECT DISTINCT c.id AS client_id, c.fullname AS client_name
FROM
(
    SELECT
        t.client_id
    FROM
        textmessage t
    JOIN
        employee e ON t.created_by = e.id
    WHERE
        t.created >= NOW() - INTERVAL '1 month'
    AND e.fullname = ANY(%s)

    UNION

    SELECT
        ol.client_id
    FROM
        openphone_log ol
    JOIN
        employee e ON ol.from_ = e.phone
    WHERE
        ol.created_at_parsed >= NOW() - INTERVAL '1 month'
    AND ol.direction = 'outgoing'
    AND e.fullname = ANY(%s)
) as combined
JOIN
    public.client c ON combined.client_id = c.id
ORDER BY client_id;
"""

fetch_records_query_template = f"""
(
    SELECT
        to_char(t.created, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
        'text_created' AS type,
        t.message AS message,
        t.client_id,
        e.fullname AS employee_name
    FROM
        textmessage t
    JOIN
        employee e ON t.created_by = e.id
    WHERE
        e.fullname = %s
        AND t.created BETWEEN '{start_time_str}' AND '{end_time_str}'
)
UNION ALL
(
    SELECT
        to_char(ol.created_at_parsed, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
        'call_created' AS type,
        NULL AS message,
        ol.client_id,
        e.fullname AS employee_name
    FROM
        openphone_log ol
    JOIN
        employee e ON ol.from_ = e.phone
    WHERE
        e.fullname = %s
        AND ol.created_at_parsed BETWEEN '{start_time_str}' AND '{end_time_str}'
        AND ol.direction = 'outgoing'
)
UNION ALL
(
    SELECT
        to_char(ol.completed_at_parsed, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
        'call_completed' AS type,
        NULL AS message,
        ol.client_id,
        e.fullname AS employee_name
    FROM
        openphone_log ol
    JOIN
        employee e ON ol.from_ = e.phone
    WHERE
        e.fullname = %s
        AND ol.completed_at_parsed BETWEEN '{start_time_str}' AND '{end_time_str}'
        AND ol.direction = 'outgoing'
)
ORDER BY
    client_id, timestamp;
"""

sql_query = f"""
SELECT
    csp.id,
    csp.client_id,
    c.fullname,
    CASE
        WHEN csp.current_stage = 1 THEN 'Stage 1: Not Interested'
        WHEN csp.current_stage = 2 THEN 'Stage 2: Initial Contact'
        WHEN csp.current_stage = 3 THEN 'Stage 3: Requirement Collection'
        WHEN csp.current_stage = 4 THEN 'Stage 4: Property Touring'
        WHEN csp.current_stage = 5 THEN 'Stage 5: Property Tour and Feedback'
        WHEN csp.current_stage = 6 THEN 'Stage 6: Application and Approval'
        WHEN csp.current_stage = 7 THEN 'Stage 7: Post-Approval and Follow-Up'
        WHEN csp.current_stage = 8 THEN 'Stage 8: Commission Collection'
        WHEN csp.current_stage = 9 THEN 'Stage 9: Dead Stage'
        ELSE 'Unknown Stage'
    END AS stage_name,
    csp.current_stage,
    csp.created_on,
    c.assigned_employee,
    c.assigned_employee_name
FROM
    client_stage_progression csp
JOIN
    client c
ON
    csp.client_id = c.id
WHERE
    csp.created_on BETWEEN '{start_time_str}' AND '{end_time_str}'
ORDER BY
    csp.created_on;
"""


def employee_record(name, df):
    temp = df[df['assigned_employee_name'] == name]

    result_df = temp.groupby('fullname')[['current_stage', 'stage_name']].agg(['min', 'max']).reset_index()
    result_df.columns = ['Client', 'min_current_stage', 'max_current_stage', 'min_stage_name', 'max_stage_name']
    result_df['change'] = result_df['max_current_stage'] - result_df['min_current_stage']
    result_df['Previous Stage'] = result_df['min_current_stage'].astype(str) + ': ' + result_df['min_stage_name'].apply(lambda x: x.split(':')[1] if ':' in x else x)
    result_df['Current Stage'] = result_df['max_current_stage'].astype(str) + ': ' + result_df['max_stage_name'].apply(lambda x: x.split(':')[1] if ':' in x else x)
    result_df['Previous Stage'] = result_df['Previous Stage'].apply(lambda x: x.split(' - ')[0])
    result_df['Current Stage'] = result_df['Current Stage'].apply(lambda x: x.split(' - ')[0])
    result_df = result_df.drop(columns=['min_current_stage', 'max_current_stage', 'min_stage_name', 'max_stage_name','change'])
    return result_df

def fetch_client_ids_and_names():
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.execute(fetch_client_ids_query, (employee_names, employee_names))
        client_data = cursor.fetchall()
        df = pd.DataFrame(client_data, columns=['client_id', 'client_name'])
        print("Client IDs and names have been loaded into a DataFrame")
        return df
    except Exception as error:
        print(f"Error fetching client data: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def fetch_and_save_records_to_csv():
    connection = None
    cursor = None
    all_records = []
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        for name in employee_names:
            cursor.execute(fetch_records_query_template, (name, name, name))
            records = cursor.fetchall()
            all_records.extend(records)
        df = pd.DataFrame(all_records, columns=['timestamp', 'type', 'message', 'client_id', 'employee_name'])
        print("Employee records have been loaded into a DataFrame")
        return df
    except Exception as error:
        print(f"Error fetching records: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def run_query_and_save_to_csv(sql_query):
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.execute(sql_query)
        records = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(records, columns=column_names)
        print("Query executed and results loaded into a DataFrame")
        return df
    except Exception as error:
        print(f"Error running query: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def add_employee_report(employee_name, df, df5):
    st.header(f'Report for {employee_name}')
    total_calls = df[df['employee_name'] == employee_name]['call_duration'].count()
    if total_calls > 0:
        st.write(f'Total Calls: {total_calls}')
    total_duration_seconds = df[df['employee_name'] == employee_name]['call_duration'].sum()
    total_duration_minutes = total_duration_seconds // 60
    total_duration_remaining_seconds = total_duration_seconds % 60
    if total_duration_minutes > 0 or total_duration_remaining_seconds > 0:
        st.write(f'Total Call Duration: {int(total_duration_minutes)} minutes {int(total_duration_remaining_seconds)} seconds')
    total_messages = df[(df['employee_name'] == employee_name) & (df['type'] == 'text_created')].shape[0]
    if total_messages > 0:
        st.write(f'Total Messages: {total_messages}')
    total_message_time_seconds = total_messages * SECONDS_PER_MESSAGE
    total_work_time_seconds = total_duration_seconds + total_message_time_seconds
    total_work_time_minutes = total_work_time_seconds // 60
    total_work_time_remaining_seconds = total_work_time_seconds % 60
    st.write(f'Assigned Time: {ASSIGNED_MINUTES} minutes')
    st.write(f'Total Work Time: {int(total_work_time_minutes)} minutes {int(total_work_time_remaining_seconds)} seconds')
    employee_calls_clients = df[(df['employee_name'] == employee_name) & (df['type'] == 'call_created')]['client_name'].dropna().unique()
    employee_messages_clients = df[(df['employee_name'] == employee_name) & (df['type'] == 'text_created')]['client_name'].dropna().unique()
    unique_clients = pd.Series(list(set(employee_calls_clients) | set(employee_messages_clients))).dropna().unique()
    num_clients = len(unique_clients)
    if num_clients > 0:
        st.write(f'Number of Clients Handled: {num_clients}')
    employee_df = employee_record(employee_name, df5)
    if not employee_df.empty:
        st.write("Employee Records:")
        st.dataframe(employee_df)

def generate_combined_streamlit_report(df, df5):
    st.title('Combined Employee Report')
    employee_names = df['employee_name'].unique()
    for employee_name in employee_names:
        add_employee_report(employee_name, df, df5)

def show_sales_rep_daily_report():
    df5 = run_query_and_save_to_csv(sql_query)
    df5 = df5.drop_duplicates(subset=['client_id', 'current_stage'])
    df5 = df5[df5['current_stage'] != 9]

    client_ids = {}
    df = fetch_client_ids_and_names()
    for index, row in df.iterrows():
        client_ids[row['client_id']] = row['client_name']

    df = fetch_and_save_records_to_csv()
    df.drop('message', axis=1, inplace=True)
    df['time_stamp'] = pd.to_datetime(df['timestamp'])

    for i in range(len(df) - 1):
        if df.loc[i, 'type'] == 'call_created' and df.loc[i+1, 'type'] == 'call_completed':
            start_unix = df.loc[i, 'time_stamp'].timestamp()
            end_unix = df.loc[i+1, 'time_stamp'].timestamp()
            duration = end_unix - start_unix
            df.loc[i, 'call_duration'] = duration

    df['client_name'] = df['client_id'].map(client_ids)
    df = df[df['type'] != 'call_completed']
    df.loc[(df['type'] == 'call_created') & (df['call_duration'].isnull()), 'call_duration'] = 0

    for index, row in df.iterrows():
        if row['call_duration'] == 0:
            df.loc[index, 'call_duration'] = df[df['employee_name'] == row['employee_name']]['call_duration'].mean()

    df.drop('time_stamp', axis=1, inplace=True)

    ASSIGNED_MINUTES = 480
    SECONDS_PER_MESSAGE = 5

    generate_combined_streamlit_report(df, df5)