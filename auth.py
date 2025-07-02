from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
print(st.secrets["google"]["type"])

# AUTH
def authenticate():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google"]
    print(creds_dict)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return creds
