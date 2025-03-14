import streamlit as st

import os
import psycopg2
import pandas as pd
import json
import requests
from urllib.parse import urlparse

from datetime import datetime, timedelta

ASSIGNED_MINUTES = 480
SECONDS_PER_MESSAGE = 5

# Add Sling API configuration
class Config:
    SLING_API_BASE = "https://api.getsling.com/v1"
    SLING_API_KEY = st.secrets.get("sling", {}).get("API_KEY", "")
    SLING_ORG_ID = st.secrets.get("sling", {}).get("ORG_ID", "")

db_params = {
    'dbname': st.secrets["database"]["DB_NAME"],
    'user': st.secrets["database"]["DB_USER"],
    'password': st.secrets["database"]["DB_PASSWORD"],
    'host': st.secrets["database"]["DB_HOST"],
    'port': st.secrets["database"]["DB_PORT"]
}

# # For debugging
# print(f"Database connection parameters:")
# print(f"Host: {db_params['host']}")
# print(f"Database: {db_params['dbname']}")
# print(f"User: {db_params['user']}")
# print(f"Port: {db_params['port']}")

employee_names = ['Mukund Chopra','John Green', 'Hiba Siddiqui','Travis Grey','John Reed','Joshua weller','Shanzay Adams', 'SOVIT BISWAL', 'Emma Paul','Omar Rogers','Ruby Smith', 'Brian Baik', 'BPO Diligence']

# Default date range calculation - will be overridden by user selection
end_time = datetime.now()
start_time = end_time - timedelta(days=1)
start_time = start_time.replace(hour=13, minute=0, second=0)
end_time = start_time + timedelta(hours=12)
start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
print(f"Start time: {start_time_str}")
print(f"End time: {end_time_str}")

# Add AttendanceAnalyzer class
class AttendanceAnalyzer:
    def __init__(self, start_date, end_date):
        self.api_base = Config.SLING_API_BASE
        self.headers = {'Authorization': Config.SLING_API_KEY}
        self.late_threshold = 15  # Consider late if arriving 15 minutes after shift start
        self.early_threshold = 15  # Consider early if leaving 15 minutes before shift end
        self.break_threshold = 60  # Maximum allowed break duration in minutes
        self.start_date = start_date
        self.end_date = end_date

    def fetch_user_data(self) -> dict:
        """Fetch all users from Sling API"""
        url = f"{self.api_base}/{Config.SLING_ORG_ID}/users"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                user_map = {
                    str(user['id']): {
                        'email': user.get('email'),
                        'name': f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
                    }
                    for user in data
                    if user.get('email')
                }
                return user_map
            return {}
        except Exception as e:
            print(f"Error fetching user data: {e}")
            return {}

    def fetch_timesheet_data(self, date: datetime) -> list:
        """Fetch timesheet data from Sling API"""
        date_str = date.strftime('%Y-%m-%d')
        date_range = f"{date_str}/{date_str}"
        nonce = int(datetime.now().timestamp() * 1000)
        
        url = f"{self.api_base}/{Config.SLING_ORG_ID}/reports/timesheets"
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={
                    'dates': date_range,
                    'nonce': nonce
                }
            )
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"Error fetching timesheet data: {e}")
            return []

    def analyze_attendance(self) -> pd.DataFrame:
        """Analyze attendance focusing on shifts and late arrivals"""
        user_map = self.fetch_user_data()
        if not user_map:
            print("No users found!")
            return pd.DataFrame()

        # Initialize tracking for each user
        attendance_records = []

        # Process each date
        current_date = self.start_date
        while current_date <= self.end_date:
            timesheet_data = self.fetch_timesheet_data(current_date)
            
            for entry in timesheet_data:
                try:
                    user_info = entry.get('user', {})
                    user_id = str(user_info.get('id'))
                    
                    if user_id not in user_map:
                        continue

                    user_name = user_map[user_id]['name']
                    
                    # Get shift details
                    shift_start = datetime.fromisoformat(entry['dtstart'].replace('Z', '+00:00'))
                    shift_end = datetime.fromisoformat(entry['dtend'].replace('Z', '+00:00'))
                    entries = entry.get('timesheetEntries', [])
                    
                    # Sort entries by timestamp for proper break calculation
                    sorted_entries = sorted(entries, key=lambda x: x['timestamp'])
                    
                    # Look for clock-in, clock-out, and breaks
                    clock_in = None
                    clock_out = None
                    current_break_start = None
                    breaks = []  # To store all break periods
                    total_break = timedelta(minutes=0)
                    
                    for record in sorted_entries:
                        entry_type = record.get('type')
                        timestamp = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))

                        if entry_type == 'clock_in':
                            if not clock_in:
                                clock_in = timestamp
                            if current_break_start:
                                # End of a break period
                                break_duration = timestamp - current_break_start
                                breaks.append((current_break_start, timestamp, break_duration))
                                total_break += break_duration
                                current_break_start = None
                                
                        elif entry_type in ['clock_out', 'auto_clock_out']:
                            clock_out = timestamp
                            if not current_break_start:
                                current_break_start = timestamp
                        
                        elif entry_type == 'break_start':
                            current_break_start = timestamp
                        elif entry_type == 'break_end' and current_break_start:
                            break_duration = timestamp - current_break_start
                            breaks.append((current_break_start, timestamp, break_duration))
                            total_break += break_duration
                            current_break_start = None
                    
                    # Calculate late minutes and early out minutes
                    late_minutes = 0
                    early_out_minutes = 0
                    
                    if clock_in:
                        minutes_late = (clock_in - shift_start).total_seconds() / 60
                        if minutes_late > self.late_threshold:
                            late_minutes = round(minutes_late)
                    
                    if clock_out:
                        minutes_early = (shift_end - clock_out).total_seconds() / 60
                        if minutes_early > self.early_threshold:
                            early_out_minutes = round(minutes_early)
                    
                    # Calculate total break duration in minutes
                    total_break_minutes = total_break.total_seconds() / 60
                    
                    # Calculate scheduled break duration (this is an example - adjust as needed)
                    scheduled_break_duration = 60  # Assuming 60 minutes is standard break time
                    
                    # Add record for this employee's shift
                    attendance_records.append({
                        'Date': current_date.strftime('%Y-%m-%d'),
                        'Employee Name': user_name,
                        'Scheduled Clock-in': shift_start.strftime('%H:%M'),
                        'Actual Clock-in': clock_in.strftime('%H:%M') if clock_in else 'Not Clocked In',
                        'Scheduled Clock-out': shift_end.strftime('%H:%M'),
                        'Actual Clock-out': clock_out.strftime('%H:%M') if clock_out else 'Not Clocked Out',
                        'Late Minutes': late_minutes,
                        'Early Out Minutes': early_out_minutes,
                        'Scheduled Break Duration': scheduled_break_duration,
                        'Actual Break Taken': round(total_break_minutes)
                    })

                except Exception as e:
                    print(f"Error processing entry: {str(e)}")
                    continue
            
            current_date += timedelta(days=1)

        return pd.DataFrame(attendance_records)

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
        call.client_id
    FROM
        call
    JOIN
        employee e ON call.employee_id = e.id
    WHERE
        call.created >= NOW() - INTERVAL '1 month'
    AND call.is_incoming = false
    AND e.fullname = ANY(%s)
) as combined
JOIN
    public.client c ON combined.client_id = c.id
ORDER BY client_id;
"""

def get_fetch_records_query(start_time_str, end_time_str):
    return f"""
    (
        SELECT
            to_char(t.created, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
            'text_created' AS type,
            t.message AS message,
            t.client_id,
            e.fullname AS employee_name,
            NULL AS call_duration
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
            to_char(c.created, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
            'call' AS type,
            c.note AS message,
            c.client_id,
            e.fullname AS employee_name,
            c.duration AS call_duration
        FROM
            call c
        JOIN
            employee e ON c.employee_id = e.id
        WHERE
            e.fullname = %s
            AND c.created BETWEEN '{start_time_str}' AND '{end_time_str}'
            AND c.is_incoming = false
    )
    ORDER BY
        client_id, timestamp;
    """

def get_stage_progression_query(start_time_str, end_time_str):
    return f"""
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
        st.error(f"Error connecting to database: {error}")
        print(f"Error fetching client data: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def fetch_and_save_records_to_csv(start_time_str, end_time_str):
    connection = None
    cursor = None
    all_records = []
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        query = get_fetch_records_query(start_time_str, end_time_str)
        for name in employee_names:
            cursor.execute(query, (name, name))
            records = cursor.fetchall()
            all_records.extend(records)
        df = pd.DataFrame(all_records, columns=['timestamp', 'type', 'message', 'client_id', 'employee_name', 'call_duration'])
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

def add_employee_report(employee_name, df, df5, attendance_df=None):
    st.header(f'Report for {employee_name}')
    
    # Calculate work activity metrics
    total_calls = df[(df['employee_name'] == employee_name) & (df['type'] == 'call')].shape[0]
    total_duration_seconds = df[(df['employee_name'] == employee_name) & (df['type'] == 'call')]['call_duration'].sum()
    total_duration_minutes = total_duration_seconds // 60
    total_messages = df[(df['employee_name'] == employee_name) & (df['type'] == 'text_created')].shape[0]
    total_message_time_seconds = total_messages * SECONDS_PER_MESSAGE
    total_work_time_seconds = total_duration_seconds + total_message_time_seconds
    total_work_time_minutes = total_work_time_seconds // 60
    
    employee_calls_clients = df[(df['employee_name'] == employee_name) & (df['type'] == 'call')]['client_id'].dropna().unique()
    employee_messages_clients = df[(df['employee_name'] == employee_name) & (df['type'] == 'text_created')]['client_id'].dropna().unique()
    unique_clients = pd.Series(list(set(employee_calls_clients) | set(employee_messages_clients))).dropna().unique()
    num_clients = len(unique_clients)
    
    # Create a combined activity table
    st.subheader("Employee Performance Summary")
    
    # Combine work activity metrics
    combined_data = {
        "Metric": [],
        "Value": []
    }
    
    # Add work activity metrics
    work_metrics = {
        "Total Calls": str(total_calls),
        "Total Call Duration (min)": str(int(total_duration_minutes)),
        "Total Messages": str(total_messages),
        "Assigned Time (min)": str(ASSIGNED_MINUTES),
        "Total Work Time (min)": str(int(total_work_time_minutes)),
        "Clients Handled": str(num_clients)
    }
    
    # Add metrics
    for metric, value in work_metrics.items():
        combined_data["Metric"].append(metric)
        combined_data["Value"].append(value)
    
    # Create and display the combined dataframe
    combined_df = pd.DataFrame(combined_data)
    st.table(combined_df)
    
    # Show detailed attendance information if available
    if attendance_df is not None and not attendance_df.empty:
        # Extract first and last name for better matching
        employee_parts = employee_name.split()
        last_name = employee_parts[-1] if len(employee_parts) > 0 else ""
        first_name = employee_parts[0] if len(employee_parts) > 0 else ""
        
        # Try different matching strategies
        employee_attendance = attendance_df[attendance_df['Employee Name'] == employee_name]
        if employee_attendance.empty and last_name:
            employee_attendance = attendance_df[attendance_df['Employee Name'].str.contains(last_name, case=False)]
        if employee_attendance.empty and first_name:
            employee_attendance = attendance_df[attendance_df['Employee Name'].str.contains(first_name, case=False)]
        
        if not employee_attendance.empty:
            st.subheader("Attendance Details")
            
            # Format the attendance dataframe for better display
            display_df = employee_attendance.copy()
            
            # Sort by date
            display_df = display_df.sort_values(by='Date')
            
            # Select and reorder columns for display
            display_columns = ['Date', 'Scheduled Clock-in', 'Actual Clock-in', 'Late Minutes',
                              'Scheduled Clock-out', 'Actual Clock-out', 'Early Out Minutes',
                              'Scheduled Break Duration', 'Actual Break Taken']
            
            display_df = display_df[display_columns]
            
            # Apply styling to highlight issues - using the newer map method instead of applymap
            def highlight_late_minutes(val):
                if val > 0:
                    return 'background-color: #ffcccc'
                return ''
            
            def highlight_early_out_minutes(val):
                if val > 0:
                    return 'background-color: #ffcccc'
                return ''
            
            def highlight_break_duration(val):
                if val > 60:  # Assuming 60 min is standard break
                    return 'background-color: #ffcccc'
                return ''
            
            # Apply the styling using map instead of applymap
            styled_df = display_df.style.map(
                highlight_late_minutes, 
                subset=['Late Minutes']
            ).map(
                highlight_early_out_minutes, 
                subset=['Early Out Minutes']
            ).map(
                highlight_break_duration, 
                subset=['Actual Break Taken']
            )
            
            st.dataframe(styled_df)
    
    # Show client progression information
    employee_df = employee_record(employee_name, df5)
    if not employee_df.empty:
        st.subheader("Client Progression")
        st.dataframe(employee_df)

def generate_combined_streamlit_report(df, df5, attendance_df=None):
    # Use a more specific title
    st.header('Employee Performance Reports')
    
    # Get unique employee names
    employee_names = df['employee_name'].unique()
    
    # Convert NumPy array to list before passing to st.tabs()
    employee_names_list = employee_names.tolist()
    
    # Create tabs for each employee
    tabs = st.tabs(employee_names_list)
    
    # Generate report for each employee in their own tab
    for i, employee_name in enumerate(employee_names):
        with tabs[i]:
            add_employee_report(employee_name, df, df5, attendance_df)
        
def show_sales_rep_daily_report():
    # Add date selection at the top
    st.subheader("Select Date Range")
    
    # Calculate default date range
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    default_start = yesterday.replace(hour=13, minute=0, second=0)
    default_end = default_start + timedelta(hours=12)
    
    # Create date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            default_start.date(),
            format="MM/DD/YYYY",
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            default_end.date(),
            format="MM/DD/YYYY",
        )
    
    # Add time selection
    col3, col4 = st.columns(2)
    with col3:
        start_time = st.time_input("Start Time", default_start.time())
    with col4:
        end_time = st.time_input("End Time", default_end.time())
    
    # Combine date and time
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)
    
    # Format for SQL queries
    start_time_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S')
    
    # Display selected range
    st.info(f"Showing data from {start_time_str} to {end_time_str}")
    
    # Fetch attendance data
    attendance_df = None
    with st.spinner("Fetching attendance data..."):
        attendance_analyzer = AttendanceAnalyzer(start_datetime, end_datetime)
        attendance_df = attendance_analyzer.analyze_attendance()
        
        if attendance_df.empty:
            st.warning("No attendance data found for the selected date range.")
    
    # Get the stage progression query with the selected date range
    stage_query = get_stage_progression_query(start_time_str, end_time_str)
    
    # Run queries with the selected date range
    df5 = run_query_and_save_to_csv(stage_query)
    
    if df5 is not None and not df5.empty:
        df5 = df5.drop_duplicates(subset=['client_id', 'current_stage'])
        df5 = df5[df5['current_stage'] != 9]

        client_ids = {}
        df = fetch_client_ids_and_names()
        if df is not None:
            for index, row in df.iterrows():
                client_ids[row['client_id']] = row['client_name']

            # Fetch records with the selected date range
            df = fetch_and_save_records_to_csv(start_time_str, end_time_str)
            
            if df is not None and not df.empty:
                # Ensure call_duration is numeric
                df['call_duration'] = pd.to_numeric(df['call_duration'], errors='coerce').fillna(0)
                
                # Map client IDs to client names
                df['client_name'] = df['client_id'].map(client_ids)
                
                # Add a divider before individual reports
                st.markdown("---")
                
                generate_combined_streamlit_report(df, df5, attendance_df)
            else:
                st.warning("No employee activity records found for the selected date range.")
        else:
            st.error("Failed to fetch client data.")
    else:
        st.warning("No stage progression data found for the selected date range.")

def main():
    try:
        # Show the sales rep daily report
        show_sales_rep_daily_report()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)

# Run the app
if __name__ == "__main__":
    main()