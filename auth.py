from oauth2client.service_account import ServiceAccountCredentials


# AUTH
def authenticate():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("D:\PycharmProjects\Crew_manager\credentials.json", scope)
    return creds
