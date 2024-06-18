# services.py

import requests
from openai import OpenAI
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bson import ObjectId
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def fetch_boards():
    jira_domain = os.getenv('JIRA_DOMAIN')
    jira_email = os.getenv('JIRA_EMAIL')
    jira_api_token = os.getenv('JIRA_API_TOKEN')

    auth_string = f"{jira_email}:{jira_api_token}"
    auth_header = base64.b64encode(auth_string.encode()).decode()

    url = f"https://{jira_domain}/rest/agile/1.0/board"
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_sprint_data(board_id):
    jira_domain = os.getenv('JIRA_DOMAIN')
    jira_email = os.getenv('JIRA_EMAIL')
    jira_api_token = os.getenv('JIRA_API_TOKEN')

    auth_string = f"{jira_email}:{jira_api_token}"
    auth_header = base64.b64encode(auth_string.encode()).decode()

    base_url = f"https://{jira_domain}/rest/agile/1.0/board/{board_id}/sprint"
    response = requests.get(
        base_url,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json"
        }
    )
    response.raise_for_status()
    sprints_data = response.json()['values']
    current_sprint = next((sprint for sprint in sprints_data if sprint['state'] == 'active'), None)

    if current_sprint:
        sprint_details_url = f"https://{jira_domain}/rest/agile/1.0/sprint/{current_sprint['id']}/issue"
        sprint_details = requests.get(
            sprint_details_url,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json"
            }
        )
        sprint_details.raise_for_status()

        tickets = [
            {
                "key": issue['key'],
                "summary": issue['fields']['summary'],
                "status": issue['fields']['status']['name']
            }
            for issue in sprint_details.json()['issues']
        ]

        sprint_summary = f"Sprint {current_sprint['name']} has {len(tickets)} tickets:\n" + \
                         "\n".join([f"{ticket['key']}: {ticket['summary']} [{ticket['status']}]" for ticket in tickets])

        return {
            "name": current_sprint['name'],
            "tickets": tickets,
            "summary": sprint_summary
        }
    return None

def summarize_data(data):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the following sprint data: {data}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing data: {e}")
    return "Summary could not be generated."

def send_email(subject, body, to):
    EMAIL = os.getenv('EMAIL')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = to
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(EMAIL, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL, to, text)
    except Exception as e:
        print(f"Error sending email: {e}")

def convert_objectid(obj):
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj