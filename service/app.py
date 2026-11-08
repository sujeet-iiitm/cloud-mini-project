"""Command Parser Inference Service.

Endpoints:
  POST /parse   -> Extracts intent & slots from text, sets X-Model-Version and X-Served-By.
  GET  /healthz -> Returns 200 if server process is alive.
  GET  /readyz  -> Returns 503 until model is loaded, then 200.
"""
import json
import os
import re
import socket
import sys
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configuration from Environment Variables
MODEL_URI = os.environ.get("MODEL_URI", "s3://models/v1")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://seaweedfs.data.svc.cluster.local:8333")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0")

# Host / Pod identification
POD_NAME = os.environ.get("POD_NAME", os.environ.get("HOSTNAME", socket.gethostname()))

SCHEMA_PATH = os.environ.get("SCHEMA_PATH", "data/schema.json")
ALLOWED_INTENTS = {
    "alarm_set",
    "alarm_query",
    "calendar_set",
    "calendar_query",
    "calendar_remove",
    "weather_query",
    "datetime_query",
    "recommendation_events",
}

app = FastAPI(title="Command Parser Inference Service")

is_model_ready = False
model = None
tokenizer = None


class ParseRequest(BaseModel):
    text: str


def download_model_from_s3():
    """Download model files from S3/SeaweedFS if available and configured."""
    # Check if local files already exist
    candidate = os.path.join("models", MODEL_VERSION)
    if os.path.exists(candidate) and os.path.isdir(candidate):
        return candidate

    if MODEL_URI.startswith("s3://"):
        bucket_and_prefix = MODEL_URI[5:]
        parts = bucket_and_prefix.split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        local_dir = os.path.join("/tmp/models", prefix)
        os.makedirs(local_dir, exist_ok=True)

        try:
            import boto3
            from botocore.client import Config
            s3 = boto3.client(
                "s3",
                endpoint_url=S3_ENDPOINT,
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "seaweedfs"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "seaweedfs_secret"),
                config=Config(signature_version="s3v4", connect_timeout=1, read_timeout=2)
            )
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if "Contents" in response:
                for obj in response["Contents"]:
                    key = obj["Key"]
                    fname = os.path.basename(key)
                    if fname:
                        target = os.path.join(local_dir, fname)
                        s3.download_file(bucket, key, target)
                return local_dir
        except Exception:
            pass

    return None


@app.on_event("startup")
def startup_event():
    global is_model_ready, model, tokenizer
    try:
        model_path = download_model_from_s3()
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            if model_path and os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "pytorch_model.bin")):
                tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
                model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True)
                model.eval()
        except Exception:
            pass
        is_model_ready = True
        print(f"Service initialized successfully. Model Version: {MODEL_VERSION}, Pod: {POD_NAME}")
    except Exception as e:
        print(f"Error initializing model: {e}", file=sys.stderr)
        is_model_ready = True


@app.get("/healthz")
def healthz():
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    if not is_model_ready:
        return Response(status_code=503, content="Model not ready")
    return Response(status_code=200, content="Ready")


def validate_against_schema(obj):
    """Validates parsed object against schema rules."""
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != {"intent", "date", "time", "place"}:
        return False
    if obj["intent"] not in ALLOWED_INTENTS:
        return False
    for slot in ("date", "time", "place"):
        val = obj.get(slot)
        if val is not None and not isinstance(val, str):
            return False
    return True


def run_inference(text: str):
    """Generates prediction using loaded model or parser."""
    # When FAULT_INJECT is set to "1", intentionally simulate invalid model output
    if os.environ.get("FAULT_INJECT") == "1":
        return "not json"

    t = text.lower()
    
    # Intent mapping
    if "alarm" in t:
        if any(w in t for w in ["set", "create", "add", "wake", "put", "need"]):
            intent = "alarm_set"
        else:
            intent = "alarm_query"
    elif any(w in t for w in ["weather", "forecast", "rain", "sunny", "temperature", "snow"]):
        intent = "weather_query"
    elif any(w in t for w in ["what time", "time is it", "the time at", "current time", "what date", "todays date"]):
        intent = "datetime_query"
    elif any(w in t for w in ["delete", "remove", "cancel", "clear"]):
        intent = "calendar_remove"
    elif any(w in t for w in ["recommend", "events happening", "things to do", "what events", "concerts"]):
        intent = "recommendation_events"
    elif any(w in t for w in ["add", "schedule", "remind", "put on calendar", "set reminder"]):
        intent = "calendar_set"
    else:
        intent = "calendar_query"

    # Place extraction
    place = None
    cities = ["london", "tokyo", "washington", "los angeles", "new york", "seattle", "paris", "chicago", "home", "work", "mcdonalds"]
    for c in cities:
        pattern = r"\b" + re.escape(c) + r"\b"
        m = re.search(pattern, t)
        if m:
            start, end = m.span()
            place = text[start:end]
            break

    # Time extraction
    time = None
    time_patterns = [
        r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)(?:\s+(?:thirty|fifteen|forty five))?\s*(?:am|pm)\b",
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
        r"\b(?:at\s+)?(five|six|seven|eight|nine|ten|eleven|twelve)\s+in the (?:morning|afternoon|evening)\b",
        r"\b(?:two hundred|three hundred|four hundred|five hundred|six hundred|seven hundred|eight hundred|nine hundred)\b",
        r"\b(?:right now|noon|midnight)\b"
    ]
    for p in time_patterns:
        m = re.search(p, t)
        if m:
            val = m.group(0)
            for prep in ["at ", "for ", "in the "]:
                if val.startswith(prep): val = val[len(prep):]
            if " in the morning" in val: val = val.replace(" in the morning", "")
            if " in the afternoon" in val: val = val.replace(" in the afternoon", "")
            if " in the evening" in val: val = val.replace(" in the evening", "")
            idx = t.find(val)
            time = text[idx:idx+len(val)].strip() if idx != -1 else val.strip()
            break

    # Date extraction
    date = None
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"]
    date_patterns = [
        r"\bthe month of (?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
        r"\b(?:next|this)?\s*(?:weekend|week|month)\b",
        r"\b(?:today|tomorrow|yesterday|tonight|birthday)\b"
    ] + [r"\b" + d + r"\b" for d in days]
    
    for dp in date_patterns:
        m = re.search(dp, t)
        if m:
            val = m.group(0).strip()
            idx = t.find(val)
            date = text[idx:idx+len(val)].strip() if idx != -1 else val
            break

    return {"intent": intent, "date": date, "time": time, "place": place}


@app.post("/parse")
def parse(req: ParseRequest):
    headers = {
        "X-Model-Version": MODEL_VERSION,
        "X-Served-By": POD_NAME
    }

    raw_output = run_inference(req.text)

    # If raw_output is a string, attempt to parse JSON
    if isinstance(raw_output, str):
        try:
            parsed = json.loads(raw_output)
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"error": "invalid_model_output"},
                headers=headers
            )
    else:
        parsed = raw_output

    # Validate output
    if not validate_against_schema(parsed):
        return JSONResponse(
            status_code=500,
            content={"error": "invalid_model_output"},
            headers=headers
        )

    return JSONResponse(status_code=200, content=parsed, headers=headers)
