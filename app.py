import streamlit as st
import pandas as pd
import gspread
from datetime import date
import auth
from streamlit_calendar import calendar
import plotly.express as px
from datetime import datetime, timedelta


today = pd.Timestamp(datetime.today().date())

creds = auth.authenticate()
client = gspread.authorize(creds)
sheet = client.open("CrewAssignments").sheet1

# FUNCTIONS
def load_data():
    return pd.DataFrame(sheet.get_all_records())

def add_crew(name, rank, vessel, embark, contract, disembark, status):
    last_row = len(sheet.get_all_values())
    next_id = last_row  # or last_row - 1 if header counts
    sheet.append_row([next_id, name, rank, vessel, embark, contract, disembark, status])

def update_crew(row_idx, data):
    for col_idx, value in enumerate(data, start=2):  # skip ID
        sheet.update_cell(row_idx, col_idx, value)

def delete_crew(row_idx):
    sheet.delete_rows(row_idx)

def is_valid_name(s):
    return s.strip() != "" and not any(char.isdigit() for char in s)

def mark_due_for_relief_and_overdue(df, sheet, warning_days=0):
    today = pd.Timestamp(date.today())
    updates_made = 0

    for i, row in df.iterrows():
        try:
            end_date = pd.to_datetime(row["Sign on Date"]) + pd.to_timedelta(int(row["Contract Days"]), unit="D")
            current_status = row["Status"]
            gsheet_row = i + 2  # GSheet offset

            if current_status == "On board":
                if end_date < today:
                    sheet.update_cell(gsheet_row, 8, "Overdue for Relief")
                    updates_made += 1
                elif 0 <= (end_date - today).days <= warning_days:
                    sheet.update_cell(gsheet_row, 8, "Due for Relief")
                    updates_made += 1
        except Exception as e:
            print(f"Failed at row {i}: {e}")

    return updates_made

# UI

df = load_data()
updates = mark_due_for_relief_and_overdue(df, sheet, warning_days=7)  # e.g. within 7 days
if updates > 0:
    st.info(f"🔄 Updated {updates} statuses to 'Due for Relief' or 'Overdue for Relief'")
    df = load_data()

st.subheader("Crew list")
# Get unique vessels and statuses, add "All" option
vessels = ["All"] + sorted(df["Vessel"].unique().tolist())
statuses = ["All", "On board", "On Leave", "Due for Relief", "Overdue for Relief"]

selected_vessel = st.selectbox("Filter by Vessel", vessels)
selected_status = st.selectbox("Filter by Status", statuses)

# Filter DataFrame accordingly
filtered_df = df.copy()

if selected_vessel != "All":
    filtered_df = filtered_df[filtered_df["Vessel"] == selected_vessel]

if selected_status != "All":
    filtered_df = filtered_df[filtered_df["Status"] == selected_status]

filtered_df.index = filtered_df.index + 1
st.dataframe(filtered_df, hide_index=True)


df_bar = pd.DataFrame()
df_bar["start"] = pd.to_datetime(filtered_df["Sign on Date"])
df_bar["Name"] = filtered_df["Name"]
df_bar["end"] = df_bar["start"] + pd.to_timedelta(filtered_df["Contract Days"], unit='D')
df_bar["Status"] = df["Status"]  # carry over from original
df_bar["color"] = df_bar.apply(
    lambda row: "Overdue" if row["end"] < today and row["Status"] == "On board" else "Normal",
    axis=1
)

# Format for calendar plugin
events = []
for _, row in df_bar.iterrows():
    events.append({
        "title": row["Name"],
        "start": row["start"].strftime("%Y-%m-%d"),
        "end": row["end"].strftime("%Y-%m-%d")
    })

calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek"
    },
    "editable": False,
    "navLinks": True,
    "selectable": False,
}

st.subheader("Crew change calendar")
calendar(events=events, options=calendar_options)
st.subheader("Multi-month overview")
# Create timeline chart
fig = px.timeline(
    df_bar,
    x_start="start",
    x_end="end",
    y="Name",
    color="color",  # use new tag
    title="Crew On board Timeline",
    color_discrete_map={
        "Overdue": "red",
        "Normal": "blue"},
   )

fig.update_yaxes(autorange="reversed")
fig.update_layout(showlegend=False,
    xaxis=dict(
        tickformat="%b %d, %Y",
        #  dtick=86400000.0,
        ticklabelmode="instant", # optional
        title_font=dict(size=20),
        tickfont=dict(size=18),
        rangeslider=dict(visible=True),
        rangeselector=dict(
            buttons=[
                dict(count=14, label="2w", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(step="all")
            ]
        )),
        dragmode='pan',  # or 'zoom'

yaxis=dict(
        title="Crew Member",
        title_font=dict(size=20),
        tickfont=dict(size=18)
    ),
    title_font=dict(size=20),
    width=1000,
    height=600
)

st.plotly_chart(fig, use_container_width=False)

with st.sidebar:
    st.title("⚓ Crew Change Manager")
    # CREATE
    with st.expander("➕ Add Crew Member"):
        name = st.text_input("Name")
        rank = st.text_input("Rank")
        vessel = st.text_input("Vessel")
        embark = st.date_input("Sign on Date", date.today())
        contract = st.number_input("Contract (days)", 1, 365, 90)
        disembark = st.date_input("Expected Relief Date", date.today()+timedelta(contract))
        status = st.selectbox("Status", ["On board", "On Leave", "Due for Relief", "Overdue for Relief"], key="set_status")
        if st.button("Add"):
            errors = []
            if not is_valid_name(name):
                errors.append("Name must be non-empty and not contain numbers.")
            if not rank:
                errors.append("Rank must be non-empty.")
            if not vessel:
                errors.append("Vessel must be non-empty.")
            if errors:
                for err in errors:
                    st.error(err)
            else:
                add_crew(name, rank, vessel, embark.isoformat(), contract, disembark.isoformat(), status)
                st.success("Added.")
                st.rerun()

    # UPDATE
    with st.expander("✏️ Edit Crew Member"):
        selected = st.selectbox("Select Crew to Edit", df["Name"])
        row = df[df["Name"] == selected].iloc[0]
        row_index = df[df["Name"] == selected].index[0] + 2  # +2 for GSheet offset
        new_name = st.text_input("Name", row["Name"])
        new_rank = st.text_input("Rank", row["Rank"])
        new_vessel = st.text_input("Vessel", row["Vessel"])
        new_embark = st.date_input("Embark", pd.to_datetime(row["Sign on Date"]))
        new_contract = st.number_input("Contract", 1, 365, int(row["Contract Days"]))
        new_disembark = st.date_input("Sign off Date", date.today()+timedelta(new_contract))
        new_status = st.selectbox("Status", ["On board", "On Leave", "Due for Relief", "Overdue for Relief"],
                                  index=["On board", "On Leave", "Due for Relief", "Overdue for Relief"].index(row["Status"]),
                                  key="edit_status")

        if st.button("Update"):
            errors = []
            if not is_valid_name(new_name):
                errors.append("Name must be non-empty and not contain numbers.")
            if not new_rank:
                errors.append("Rank must be non-empty.")
            if not new_vessel:
                errors.append("Vessel must be non-empty.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                update_crew(row_index, [
                    new_name,
                    new_rank,
                    new_vessel,
                    new_embark.isoformat(),
                    new_contract,
                    new_disembark.isoformat(),
                    new_status
                ])
                st.success("Updated.")
                st.rerun()

    # DELETE
    with st.expander("🗑️ Delete Crew Member"):
        to_delete = st.selectbox("Select crew to delete", df["Name"].tolist())

        if st.button("Delete"):
            try:
                # Find the row index of the name in the sheet
                # gspread rows start at 1 and first row is header, so add 2 for zero-based index + header row
                row_index = df.index[df["Name"] == to_delete].tolist()

                if not row_index:
                    st.error("Name not found!")
                else:
                    # +2: because pandas index is zero-based, and sheet has header row
                    sheet.delete_rows(row_index[0] + 2)
                    st.success(f"Deleted {to_delete} at row {row_index[0] + 2}")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to delete: {e}")

