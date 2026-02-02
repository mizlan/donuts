"""Configuration for the Slack donut bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Slack credentials
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

# Slack channel
DONUT_CHAT_CHANNEL = os.environ.get("DONUT_CHAT_CHANNEL", "donut-chat")

# Server port
PORT = int(os.environ.get("PORT", 3000))

# Send startup message
SEND_STARTUP_MESSAGE = os.environ.get("SEND_STARTUP_MESSAGE", "false").lower() == "true"

# File paths (relative to workspace root)
REGISTRY_PATH = os.environ.get("REGISTRY_PATH", "./registry.csv")
HISTORY_PATH = os.environ.get("HISTORY_PATH", "./history.csv")

# Validation
if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN environment variable not set")
if not SLACK_SIGNING_SECRET:
    raise ValueError("SLACK_SIGNING_SECRET environment variable not set")
