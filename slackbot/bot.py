"""Main entry point for the Slack donut bot."""

import csv
import json

from flask import Flask, Response, request
from flask_cors import CORS
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from . import config, handlers

print("[BOT] Starting Slack donut bot...")
print(f"[BOT] DONUT_CHAT_CHANNEL: {config.DONUT_CHAT_CHANNEL}")
print(f"[BOT] REGISTRY_PATH: {config.REGISTRY_PATH}")
print(f"[BOT] HISTORY_PATH: {config.HISTORY_PATH}")

# Initialize Slack Bolt app
bolt_app = App(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET,
)

# Register all event handlers
handlers.register_handlers(bolt_app)

print("[BOT] Event handlers registered")

# Flask app
flask_app = Flask(__name__)
CORS(flask_app)
handler = SlackRequestHandler(bolt_app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    print(f"[FLASK] Received: content_type={request.content_type}")
    response = handler.handle(request)
    print(f"[FLASK] Response status: {response.status_code}")
    return response


def load_registry() -> dict[str, str]:
    """Load registry and build email -> name mapping."""
    email_to_name = {}
    with open(config.REGISTRY_PATH) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 2:
                name, email = row[0].strip(), row[1].strip()
                email_to_name[email] = name
    return email_to_name


def normalize_name(value: str, email_to_name: dict[str, str]) -> str:
    """Convert email to name if it exists in registry, otherwise return as-is."""
    return email_to_name.get(value, value)


@flask_app.route("/chats", methods=["GET"])
def get_chats():
    email_to_name = load_registry()
    pairs = []
    with open(config.HISTORY_PATH) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 2 and row[0] and row[1]:
                pairs.append({
                    "person1": normalize_name(row[0], email_to_name),
                    "person2": normalize_name(row[1], email_to_name),
                })
    return Response(json.dumps(pairs), mimetype="application/json")


def send_startup_message():
    """Send startup message to the donut chat channel."""
    try:
        bolt_app.client.chat_postMessage(
            channel=config.DONUT_CHAT_CHANNEL,
            text="ready to donut!!!",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": "ready to donut!!!"}},
                {
                    "type": "image",
                    "image_url": "https://static.wikia.nocookie.net/pixar/images/3/35/Dug-up.jpg/revision/latest?cb=20090602035123",
                    "alt_text": "Dug is ready!",
                },
            ],
        )
        print(f"[BOT] Sent startup message to {config.DONUT_CHAT_CHANNEL}")
    except Exception as e:
        print(f"[BOT] ERROR sending startup message: {e}")


def start():
    """Start the bot server."""
    print(f"[BOT] Starting server on port {config.PORT}...")

    if config.SEND_STARTUP_MESSAGE:
        send_startup_message()

    flask_app.run(host="0.0.0.0", port=config.PORT)


if __name__ == "__main__":
    start()
