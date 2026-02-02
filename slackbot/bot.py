"""Main entry point for the Slack donut bot."""

import os
from slack_bolt import App

from . import config, handlers

print("[BOT] Starting Slack donut bot...")
print(f"[BOT] DONUT_CHAT_CHANNEL: {config.DONUT_CHAT_CHANNEL}")
print(f"[BOT] REGISTRY_PATH: {config.REGISTRY_PATH}")
print(f"[BOT] HISTORY_PATH: {config.HISTORY_PATH}")

# Initialize Slack Bolt app with HTTP mode (handles URL verification automatically)
app = App(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET,
)

print("[BOT] Slack app initialized")

# Register all event handlers
handlers.register_handlers(app)

print("[BOT] Event handlers registered")


def start():
    """Start the bot server."""
    print(f"[BOT] Starting server on port {config.PORT}...")

    # Send startup message with image
    if config.SEND_STARTUP_MESSAGE:
        try:
            app.client.chat_postMessage(
                channel=config.DONUT_CHAT_CHANNEL,
                text="ready to donut!!!",
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "ready to donut!!!"},
                    },
                    {
                        "type": "image",
                        "image_url": "https://static.wikia.nocookie.net/pixar/images/3/35/Dug-up.jpg/revision/latest?cb=20090602035123",
                        "alt_text": "Dug is ready!",
                    },
                ],
            )
            print(
                f"[BOT] Sent startup message with image to {config.DONUT_CHAT_CHANNEL}"
            )
        except Exception as e:
            print(f"[BOT] ERROR sending startup message: {e}")

    app.start(port=config.PORT)


if __name__ == "__main__":
    start()
