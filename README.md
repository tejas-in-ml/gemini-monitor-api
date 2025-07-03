emini Monitor API

This project monitors usage of Gemini models deployed on Google Cloud's AI Platform. It$


Dependencies:

flask

google-cloud-monitoring

google-auth

requests

apscheduler

Install them using:

pip install flask google-cloud-monitoring google-auth requests apscheduler

File Structure:

.
|-gcp_data_metrics.py
|
|-allowed_models.txt
|
|-media17-service-account.json


Loads whitelisted model names from allowed_models.txt

Uses the Monitoring API to fetch model usage data

Compares fetched models against the whitelist

Sends alerts to Jarvis for any unapproved model detected

Sends start, success, or error pings to Jarvis to indicate script status

Runs automatically every 5 hours using a background scheduler

Running the Server:

python3 gcp_data_metrics.py

The server will start on port 8000 and be accessible via http://<your-ip>:8000

API Endpoints:

GET /ping
Returns {"status": "pong"}
Used to check if the server is active

GET /run-monitor
Triggers the monitoring script manually and returns alert results

Security Note:

Do not commit the service account JSON file to version control. Make sure media17-servi$
