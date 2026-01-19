import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def get_scopes():
    scopes = []
    with open("scopes.txt","r") as s:
        for line in s.readlines():
            stripped_line = line.strip()
            if stripped_line:
                scopes.append(stripped_line)
    return scopes

def get_creds():
    creds = None
    scopes = get_scopes()
    token_exists = False
    if os.path.exists("token.json"): #logged in before, use toke
        creds = Credentials.from_authorized_user_file("token.json",scopes)
        token_exists = True

    if not creds or not creds.valid: #either no token or token is invalid
        if creds and creds.expired and creds.refresh_token: #token needs to be refreshed
            creds.refresh(Request())
        else: #token invalid or doesn't exist
            if token_exists:
                os.remove("token.json")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json",scopes) #instantiate an object to help log in with credentials file
            creds = flow.run_local_server(port=0) #Connect to google to login, get tokens if login is sucessful
        with open("token.json","w") as token: #new tokens, make new token file
            token.write(creds.to_json())
    return creds

def create_service(api,version):
    creds = get_creds()
    return build(api,version,credentials=creds)






            
        


