import streamlit as st
from sales_leads import show_sales_leads
from client_stage_progression import show_client_stage_progression
from low_sales_progression import show_low_sales_progression
from streamlit_autorefresh import st_autorefresh
from may_accounts_monitor import show_recent_clients
from sales_rep_report import show_sales_rep_daily_report
from building_send_clients import may_update_channel_clients

favicon = "2.png"
st.set_page_config(page_title='Homeeasy Sales Dashboard', page_icon=favicon, layout='wide', initial_sidebar_state='auto')

if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0
st.session_state.refresh_count += 1
# st.sidebar.write(f"Page refreshed {st.session_state.refresh_count} times.")
st.sidebar.write("The page will refresh automatically every hour.")

# Set the refresh interval to 1 hour 
st_autorefresh(interval=3600 * 1000, key="autoRefresh", debounce=False)
st.sidebar.title("Homeeasy Sales Leads Monitoring System")
page = st.sidebar.selectbox("Choose a report", ["Sales Leads Monitoring", "Client Stage Progression Report", "Low Sales Progression", "Sales Rep Daily Report", "May Account Assigned Clients", "May Update Channel Cilents"])
if page == "Sales Leads Monitoring":
    show_sales_leads()
elif page == "Client Stage Progression Report":
    show_client_stage_progression()
elif page == "May Account Assigned Clients":
    show_recent_clients()
elif page == "Sales Rep Daily Report":
    show_sales_rep_daily_report()
elif page == "May Update Channel Cilents":
    may_update_channel_clients()
else:
    show_low_sales_progression()
