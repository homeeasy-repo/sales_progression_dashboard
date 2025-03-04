import streamlit as st
from sales_leads import show_sales_leads
from client_stage_progression import show_client_stage_progression
from low_sales_progression import show_low_sales_progression
from streamlit_autorefresh import st_autorefresh
from may_accounts_monitor import show_recent_clients
# from sales_rep_report import show_sales_rep_daily_report
from sales_daily_report import show_sales_rep_daily_report
from building_send_clients import may_update_channel_clients
from clients_under_1000 import under_1000_budget_clients
from under_1500_clients import btw_1000_1500_budget_clients
from above_1500_deals import show_above_1500_clients
from above_2000_deals import show_above_2000_clients
from client_process_sold import show_responsive_clients
from urgent_movein import show_clients_with_urgent_movein
from reporting_11am import generate_11am_report
import streamlit.components.v1 as components

favicon = "fubicon.jpeg"
st.set_page_config(page_title='Homeeasy Sales Dashboard', page_icon=favicon, layout='wide', initial_sidebar_state='auto')

logo_path = "homeeasyLogo.png"
# st.sidebar.image(logo_path, use_column_width=True)
st.sidebar.image(logo_path, width=300)


if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0
st.session_state.refresh_count += 1
# st.sidebar.write("The page will refresh automatically every hour.")

st_autorefresh(interval=3600 * 1000, key="autoRefresh", debounce=False)
st.sidebar.title("Homeeasy Sales Leads Monitoring System")

page = st.sidebar.selectbox("Choose a report", [
    "Home", 
    "Responsive Clients",
    "Clients With Move in Date",
    "11 AM Reporting",
    "Sales Leads Monitoring", 
    "Client Stage Progression Report", 
    "Low Sales Progression", 
    "Sales Rep Daily Report", 
    "May Account Assigned Clients", 
    "May Update Channel Clients", 
    "Today's Client Under 1000$", 
    "Today's Client Between 1000$ and 1500$", 
    "Today's Clients between 1500$ and 2000$", 
    "Today's Client above 2000$"
])

if page == "Home":
    components.html("""
        <div style="font-family: system-ui; font-size: 1.2em; line-height: 1.2; text-align: center; color:#00ceffed;">
            <h2 id="introTitle"></h2>
            <p id="introDesc"></p>
            <h3 id="title1"></h3>
            <p id="desc1"></p>
            <h3 id="title2"></h3>
            <p id="desc2"></p>
            <h3 id="title3"></h3>
            <p id="desc3"></p>
            <h3 id="title4"></h3>
            <p id="desc4"></p>
            <h3 id="title5"></h3>
            <p id="desc5"></p>
            <h3 id="title6"></h3>
            <p id="desc6"></p>
            <h3 id="title7"></h3>
            <p id="desc7"></p>
            <h3 id="title8"></h3>
            <p id="desc8"></p>
            <h3 id="title9"></h3>
            <p id="desc9"></p>
            <h3 id="title10"></h3>
            <p id="desc10"></p>
            <p id="outroText"></p>
        </div>
        <script>
            const texts = [
                { title: "Welcome to the Homeeasy Sales Dashboard", desc: "This dashboard is designed to help you monitor and analyze sales leads and client progress effectively. Below is an overview of each report available in this dashboard:" },
                { title: "1. Sales Leads Monitoring", desc: "View and track the latest sales leads with details about the client, assigned employee, and the status of interactions." },
                { title: "2. Client Stage Progression Report", desc: "Analyze the progression of clients through various sales stages to understand where clients stand in the sales pipeline." },
                { title: "3. Low Sales Progression", desc: "Identify clients or leads with low engagement or slow progression to address potential issues in the sales process." },
                { title: "4. Sales Rep Daily Report", desc: "Review daily activities of each sales representative to assess performance and productivity." },
                { title: "5. May Account Assigned Clients", desc: "Monitor clients assigned to the 'May Account' for special handling or follow-up actions." },
                { title: "6. May Update Channel Clients", desc: "Keep track of clients needing updates through the May Channel." },
                { title: "7. Today's Client Under 1000$", desc: "View clients whose budget falls under $1000 for today, allowing tailored strategies for smaller budgets." },
                { title: "8. Today's Client Between 1000$ and 1500$", desc: "Focus on clients with a budget between $1000 and $1500 to identify and address specific needs." },
                { title: "9. Today's Clients between 1500$ and 2000$", desc: "View clients whose budget is between $1500 and $2000, for potential upsell or targeted marketing efforts." },
                { title: "10. Today's Client above 2000$", desc: "Target clients with a budget above $2000 to maximize high-value sales opportunities." },
                { title: "", desc: "Please select a report from the sidebar to begin analyzing specific data." }
            ];

            function typeWriter(text, elementId, delay) {
                let index = 0;
                function type() {
                    const element = document.getElementById(elementId);
                    if (element && index < text.length) {
                        element.innerHTML += text.charAt(index);
                        index++;
                        setTimeout(type, delay);
                    }
                }
                type();
            }

            function animate() {
                texts.forEach((item, idx) => {
                    setTimeout(() => {
                        if (idx === 0) {
                            typeWriter(item.title, 'introTitle', 30); // Faster title typing
                            setTimeout(() => typeWriter(item.desc, 'introDesc', 20), 500); // Faster description typing
                        } else if (idx === texts.length - 1) {
                            typeWriter(item.desc, 'outroText', 20);
                        } else {
                            typeWriter(item.title, 'title' + idx, 30);
                            setTimeout(() => typeWriter(item.desc, 'desc' + idx, 20), 500);
                        }
                    }, idx * 2000); // Slightly faster overall display timing
                });
            }

            animate();
        </script>
    """, height=1500, scrolling=True)

elif page == "Sales Leads Monitoring":
    show_sales_leads()
elif page == "Responsive Clients":
    show_responsive_clients()
elif page == "Clients With Move in Date":
    show_clients_with_urgent_movein()
elif page == "11 AM Reporting":
    generate_11am_report()
elif page == "Client Stage Progression Report":
    show_client_stage_progression()
elif page == "May Account Assigned Clients":
    show_recent_clients()
elif page == "Sales Rep Daily Report":
    show_sales_rep_daily_report()
elif page == "May Update Channel Clients":
    may_update_channel_clients()
elif page == "Today's Client Under 1000$":
    under_1000_budget_clients()
elif page == "Today's Client Between 1000$ and 1500$":
    btw_1000_1500_budget_clients()
elif page == "Today's Clients between 1500$ and 2000$":
    show_above_1500_clients()  
elif page == "Today's Client above 2000$":
    show_above_2000_clients()
else:
    show_low_sales_progression()
