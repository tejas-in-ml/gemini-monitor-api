from flask import Flask, jsonify
from google.cloud import monitoring_v3
from google.oauth2 import service_account
from google.protobuf.timestamp_pb2 import Timestamp
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import json

app = Flask(__name__)

# -- Service Account Credentials 
SERVICE_ACCOUNT_FILE = "/home/ubuntu/media17-service-account.json"
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
client = monitoring_v3.MetricServiceClient(credentials=credentials)
PROJECT_NUMBER = "451294962789"
project_name = f"projects/{PROJECT_NUMBER}"

# -- Ping Jarvis
def ping_jarvis(status):
    try:
        requests.get("https://monitor-prod.ml17.live/monitor/api/send-alert", params={
            "service-name": "gemini-monitor",
            "alert-message": f"Script {status}",
            "parameter": 0
        })
    except Exception as e:
        print(f"Ping failed: {e}")

# -- Load Allowed Models 
def load_allowed_models():
    try:
        with open("/home/ubuntu/allowed_models.txt") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"Error loading allowed models: {e}")
        return set()

# -- Alert Function 
def alert(msg):
    try:
        requests.get("https://monitor-prod.ml17.live/monitor/api/send-alert", params={
            "service-name": "gemini-model-usage",
            "alert-message": msg,
            "parameter": 10
        })
    except Exception as e:
        print(f"Alert send failed: {e}")

# -- Main Monitoring Logic 
def run_monitoring():
    allowed_models = load_allowed_models()
    region_model_map = defaultdict(set)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)

    interval = monitoring_v3.TimeInterval(
        start_time=Timestamp(seconds=int(start.timestamp())),
        end_time=Timestamp(seconds=int(end.timestamp())),
    )

    filter_str = (
        'metric.type = "aiplatform.googleapis.com/publisher/online_serving/character_count" '
        'AND resource.type = "aiplatform.googleapis.com/PublisherModel"'
    )

    try:
        ping_jarvis("start")

        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": filter_str,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        alerts_sent = []

        for ts in results:
            region = ts.resource.labels.get('location') or 'global'
            model = ts.resource.labels.get('model_user_id')
            if model:
                region_model_map[region].add(model)

        for region, models in region_model_map.items():
            bad_models = [m for m in models if m not in allowed_models]
            if bad_models:
                msg = f"Unapproved models from region {region}: {', '.join(bad_models)}"
                alert(msg)
                alerts_sent.append(msg)

        ping_jarvis("success")
        return {"status": "success", "alerts": alerts_sent}

    except Exception as e:
        ping_jarvis("error")
        alert(f"Error fetching Gemini model usage: {e}")
        return {"status": "error", "details": str(e)}

# ===== API Endpoints =====
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "pong"})

@app.route("/run-monitor", methods=["GET"])
def run_monitor():
    result = run_monitoring()
    return jsonify(result)

@app.route("/add-model", methods=["POST"])
def add_model():
    model = request.json.get("model")
    if not model:
        return jsonify({"status": "error", "message": "No model provided"}), 400
    
    try:
        with open(allowed_models, "a") as f:
            f.write(model.strip() + "\n")
        return jsonify({"status": "success", "message": f"Model '{model}' added"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/remove-model", methods=["DELETE"])
def remove_model():
    model = request.json.get("model")
    if not model:
        return jsonify({"status": "error", "message": "No model provided"}), 400

    try:
        with open(allowed_models, "r") as f:
            models = [line.strip() for line in f if line.strip() != model.strip()]
        with open(allowed_models, "w") as f:
            for m in models:
                f.write(m + "\n")
        return jsonify({"status": "success", "message": f"Model '{model}' removed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

scheduler = BackgroundScheduler()
scheduler.add_job(run_monitoring, 'interval', minutes=5)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
    
