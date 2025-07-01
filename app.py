import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# AUTH
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("D:\PycharmProjects\Crew_manager\credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("CrewAssignments").sheet1

# FUNCTIONS
def load_data():
    return pd.DataFrame(sheet.get_all_records())

def add_crew(name, rank, vessel, embark, contract, status):
    sheet.append_row([sheet.row_count, name, rank, vessel, embark, contract, status])

def update_crew(row_idx, data):
    for col_idx, value in enumerate(data, start=2):  # skip ID
        sheet.update_cell(row_idx, col_idx, value)

def delete_crew(row_idx):
    sheet.delete_rows(row_idx)

# UI
st.title("⚓ Crew Change Manager")
df = load_data()
st.dataframe(df)

# CREATE
with st.expander("➕ Add Crew Member"):
    name = st.text_input("Name")
    rank = st.text_input("Rank")
    vessel = st.text_input("Vessel")
    embark = st.date_input("Embark Date", date.today())
    contract = st.number_input("Contract (days)", 1, 365, 90)
    status = st.selectbox("Status", ["Onboard", "On Leave", "Due for Relief"], key="set_status")
    if st.button("Add"):
        add_crew(name, rank, vessel, embark.isoformat(), contract, status)
        st.success("Added.")
        st.experimental_rerun()

# UPDATE
with st.expander("✏️ Edit Crew Member"):
    selected = st.selectbox("Select Crew to Edit", df["Name"])
    row = df[df["Name"] == selected].iloc[0]
    row_index = df[df["Name"] == selected].index[0] + 2  # +2 for GSheet offset

    new_name = st.text_input("Name", row["Name"])
    new_rank = st.text_input("Rank", row["Rank"])
    new_vessel = st.text_input("Vessel", row["Vessel"])
    new_embark = st.date_input("Embark", pd.to_datetime(row["Embark Date"]))
    new_contract = st.number_input("Contract", 1, 365, int(row["Contract Days"]))
    new_status = st.selectbox("Status", ["Onboard", "On Leave", "Due for Relief"],
                              index=["Onboard", "On Leave", "Due for Relief"].index(row["Status"]), key="edit_status")

    if st.button("Update"):
        update_crew(row_index, [new_name, new_rank, new_vessel, new_embark.isoformat(), new_contract, new_status])
        st.success("Updated.")
        st.experimental_rerun()

# DELETE
with st.expander("🗑️ Delete Crew Member"):
    to_delete = st.selectbox("Select Crew to Delete", df["Name"])
    del_row_index = df[df["Name"] == to_delete].index[0] + 2
    if st.button("Delete"):
        delete_crew(del_row_index)
        st.warning("Deleted.")
        st.experimental_rerun()
