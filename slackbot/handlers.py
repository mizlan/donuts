"""Event handlers for the Slack donut bot."""

import re
from itertools import combinations
from slack_bolt import App

from . import slack_client, tracking, config
from src import history as history_module, solver


def register_handlers(app: App) -> None:
    """Register all event handlers with the app."""

    @app.event("app_mention")
    def handle_app_mention(event, client):
        """Respond when the bot is mentioned."""
        channel = event.get("channel")
        ts = event.get("ts")
        client.chat_postMessage(
            channel=channel,
            thread_ts=ts,
            text="🐕",
            blocks=[
                {
                    "type": "image",
                    "image_url": "https://i.ytimg.com/vi/1KHSR_Flqww/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLD-pjkiEtODTgatoYJ4KVIa1rgupA",
                    "alt_text": "Dug!",
                }
            ],
        )

    @app.command("/makedonuts")
    def handle_makedonuts(ack, command, client, say):
        """Generate and post donut pairings."""
        ack()

        try:
            # Load registry and history
            registry = history_module.parse_registry(config.REGISTRY_PATH)
            past_meetings = history_module.parse_history(registry, config.HISTORY_PATH)

            # Generate pairings
            pairs = solver.make_assignment(registry, past_meetings)

            # Format message
            text = f"*Generated {len(pairs)} donut chats:*\n"
            for person1, person2 in pairs:
                text += f"• {person1.name} ⋯ {person2.name}\n"

            # Post to donut-chat channel
            response = client.chat_postMessage(
                channel=config.DONUT_CHAT_CHANNEL, text=text
            )

            print(f"Posted pairings message to {config.DONUT_CHAT_CHANNEL}")

        except Exception as e:
            print(f"Error in /makedonuts: {e}")
            say(f"Error generating pairings: {e}")

    @app.event("message")
    def handle_message(event, client, say):
        """Listen for donut chat confirmation messages with @mentions."""

        print(f"[MESSAGE EVENT] Received: {event}")

        # Ignore bot messages and messages without mentions
        if event.get("type") != "message":
            print(f"[MESSAGE] Skipped: not a message event (type={event.get('type')})")
            return

        if event.get("bot_id"):
            print(f"[MESSAGE] Skipped: bot message (bot_id={event.get('bot_id')})")
            return

        # Skip system messages (channel_join, member_left)
        subtype = event.get("subtype")
        if subtype in ("channel_join", "member_left"):
            print(f"[MESSAGE] Skipped: system message (subtype={subtype})")
            return

        # Only process messages in donut-chat channel
        channel = event.get("channel")
        if channel != config.DONUT_CHAT_CHANNEL:
            print(
                f"[MESSAGE] Skipped: wrong channel (got={channel}, want={config.DONUT_CHAT_CHANNEL})"
            )
            return

        # Skip thread replies to avoid processing bot messages
        if event.get("thread_ts"):
            print(
                f"[MESSAGE] Skipped: thread reply (thread_ts={event.get('thread_ts')})"
            )
            return

        text = event.get("text", "")
        ts = event.get("ts")

        if not text:
            print(f"[MESSAGE] Skipped: no text")
            return

        # Extract mentions (format: <@USER_ID>)
        mentions = re.findall(r"<@([A-Z0-9]+)>", text)

        if not mentions:
            print(f"[MESSAGE] Skipped: no mentions in text")
            return

        print(f"[MESSAGE] Processing: text={text}, mentions={mentions}")

        try:
            registry = history_module.parse_registry(config.REGISTRY_PATH)
            identifier_map = _build_identifier_mapping(registry)

            # Check if at least one mention is a real person in registry
            mentioned_names = _get_valid_mentioned_names(
                mentions, client, registry, identifier_map
            )
            if not mentioned_names:
                print(f"[MESSAGE] Skipped: no valid person mentions found")
                return

            # React with white checkmark
            client.reactions_add(channel=channel, timestamp=ts, name="white_check_mark")

            # Post thread reply
            thread_reply = (
                "Please react to this message with :white_check_mark: "
                "to confirm the donut chat happened!"
            )
            client.chat_postMessage(channel=channel, thread_ts=ts, text=thread_reply)

            print(
                f"[MESSAGE] Detected donut chat with {len(mentioned_names)} valid mention(s)"
            )

        except Exception as e:
            print(f"Error in handle_message: {e}")

    @app.event("reaction_added")
    def handle_reaction(event, client):
        """Track confirmation when someone reacts with checkmark to donut chat."""

        print(f"[REACTION EVENT] Received: {event}")

        reaction = event.get("reaction")
        user_id = event.get("user")
        channel = event.get("item", {}).get("channel")
        ts = event.get("item", {}).get("ts")

        print(
            f"[REACTION] reaction={reaction}, user={user_id}, channel={channel}, ts={ts}"
        )

        if reaction != "white_check_mark":
            print(
                f"[REACTION] Skipped: wrong emoji (got={reaction}, want=white_check_mark)"
            )
            return

        if not user_id:
            print(f"[REACTION] Skipped: no user_id")
            return

        if not channel:
            print(f"[REACTION] Skipped: no channel")
            return

        if not ts:
            print(f"[REACTION] Skipped: no timestamp")
            return

        # Only process reactions in donut-chat channel
        if channel != config.DONUT_CHAT_CHANNEL:
            print(
                f"[REACTION] Skipped: wrong channel (got={channel}, want={config.DONUT_CHAT_CHANNEL})"
            )
            return

        print(
            f"[REACTION] Processing reaction: user={user_id}, channel={channel}, ts={ts}"
        )

        try:
            # Fetch the message
            print(f"[REACTION] Fetching message from {channel} at {ts}")
            msg_response = client.conversations_history(
                channel=channel, latest=ts, limit=1, inclusive=True
            )

            if not msg_response.get("messages"):
                print(f"[REACTION] ERROR: No message found at {ts}")
                return

            message = msg_response["messages"][0]
            text = message.get("text", "")
            poster_user_id = message.get("user")

            print(f"[REACTION] Message: user={poster_user_id}, text={text[:50]}...")

            # Extract mentions
            mentions = re.findall(r"<@([A-Z0-9]+)>", text)
            print(f"[REACTION] Found {len(mentions)} mention(s): {mentions}")

            if not mentions:
                print(f"[REACTION] Skipped: no mentions in message")
                return

            if not poster_user_id:
                print(f"[REACTION] Skipped: no poster_user_id")
                return

            # Get emails for poster and mentioned users
            poster_email = slack_client.get_user_email(client, poster_user_id)
            if not poster_email:
                print(f"ERROR: No email found for user {poster_user_id}")
                return

            # Look up names in registry
            registry = history_module.parse_registry(config.REGISTRY_PATH)
            identifier_map = _build_identifier_mapping(registry)

            if poster_email not in identifier_map:
                print(f"ERROR: User with email {poster_email} not found in registry")
                return

            poster_name = registry[identifier_map[poster_email]].name

            # Get mentioned people's emails and names
            mentioned_names = _get_valid_mentioned_names(
                mentions, client, registry, identifier_map
            )
            if not mentioned_names:
                print(f"[REACTION] Skipped: No valid mentions found in message {ts}")
                return

            # Record donut chat for each pair
            all_people = [poster_name] + mentioned_names
            pairs = _generate_all_pairs(all_people)
            print(f"[REACTION] Recording {len(pairs)} donut chat pair(s)...")
            for person1, person2 in pairs:
                print(f"[REACTION] Recording: {person1} <-> {person2}")
                tracking.append_to_history(person1, person2, config.HISTORY_PATH)

            # Try to strikethrough the pair in the pairings message
            _strikethrough_pair_in_message(
                client, channel, poster_name, mentioned_names
            )

            # Find and update the bot's thread reply
            print(f"[REACTION] Fetching thread replies for message {ts}")
            thread_response = client.conversations_replies(
                channel=channel, ts=ts, limit=100
            )

            bot_found = False
            for thread_msg in thread_response.get("messages", []):
                if thread_msg.get("bot_id"):
                    # Found bot's message, edit it
                    print(f"[REACTION] Updating bot message at {thread_msg['ts']}")
                    client.chat_update(
                        channel=channel, ts=thread_msg["ts"], text="✅ Recorded!"
                    )
                    bot_found = True
                    break

            if not bot_found:
                print(f"[REACTION] WARNING: No bot message found in thread")

            print(
                f"[REACTION] Success! Confirmed {len(mentioned_names)} donut chat(s): {poster_name}"
            )

        except Exception as e:
            print(f"Error in handle_reaction: {e}")


def _generate_all_pairs(people: list[str]) -> list[tuple[str, str]]:
    """Generate all unique pairs from a list of people.

    Args:
        people: List of person names

    Returns:
        List of (person1, person2) tuples
    """
    return list(combinations(people, 2))


def _build_identifier_mapping(registry: dict[int, object]) -> dict[str, int]:
    """Build identifier to ID mapping from registry."""
    mapping = {}
    for person_id, person in registry.items():
        mapping[person.name] = person_id
        mapping[person.email] = person_id
    return mapping


def _strikethrough_pair_in_message(
    client, channel: str, person1: str, person2_list: list[str]
) -> None:
    """Find and strikethrough a pair in the pairings message.

    Args:
        client: Slack client
        channel: Channel to search in
        person1: First person's name
        person2_list: List of second person's names
    """
    try:
        # Get last 50 messages from the channel, filter for bot messages with pairings
        response = client.conversations_history(channel=channel, limit=50)

        for message in response.get("messages", []):
            if not message.get("bot_id"):
                continue

            text = message.get("text", "")
            if "Generated" not in text:
                continue

            # Try to find and strikethrough pairs
            lines = text.split("\n")
            updated = False

            for person2 in person2_list:
                # Look for line matching this pair (case-insensitive)
                # Handle variations like "person1 ⋯ person2" or "person1 ... person2"
                for i, line in enumerate(lines):
                    lower_line = line.lower()
                    if person1.lower() in lower_line and person2.lower() in lower_line:
                        # Don't strikethrough if already done
                        if "~" not in line:
                            lines[i] = f"~{line}~"
                            updated = True
                            print(
                                f"[STRIKETHROUGH] Found and strikethrough pair: {person1} ⋯ {person2}"
                            )
                        break

            if updated:
                new_text = "\n".join(lines)
                msg_ts = message.get("ts")
                client.chat_update(channel=channel, ts=msg_ts, text=new_text)
                print(f"[STRIKETHROUGH] Updated pairings message")
                break
    except Exception as e:
        print(f"Error strikethrough pair: {e}")


def _normalize_email(email: str) -> str:
    """Normalize email for comparison: lowercase and @g.ucla.edu -> @ucla.edu."""
    if not email:
        return email
    normalized = email.lower()
    normalized = normalized.replace("@g.ucla.edu", "@ucla.edu")
    return normalized


def _get_valid_mentioned_names(
    mentions: list[str], client, registry: dict, identifier_map: dict[str, int]
) -> list[str]:
    """Get names of valid people from mention list.

    Args:
        mentions: List of user IDs mentioned
        client: Slack client
        registry: Person registry
        identifier_map: Mapping of email/name to person ID

    Returns:
        List of names for valid mentions (people in registry), empty if none found
    """
    mentioned_names = []
    for mention_id in mentions:
        user_info = slack_client.get_user_info(client, mention_id)
        if not user_info:
            print(
                f"[VALIDATION] Skipped mention: Could not fetch user info for {mention_id}"
            )
            continue

        # Try to match by email first (with normalization), then by name
        person_id = None
        if user_info["email"]:
            normalized_email = _normalize_email(user_info["email"])
            # Check against normalized keys in identifier_map
            for key, pid in identifier_map.items():
                if (
                    key.lower() == normalized_email
                    or _normalize_email(key) == normalized_email
                ):
                    person_id = pid
                    break

        if person_id is None and user_info["real_name"]:
            # Case-insensitive name match
            normalized_name = user_info["real_name"].lower()
            for key, pid in identifier_map.items():
                if key.lower() == normalized_name:
                    person_id = pid
                    break

        if person_id is None:
            print(
                f"[VALIDATION] Skipped mention: {mention_id} ({user_info.get('email') or user_info.get('real_name')}) not in registry"
            )
            continue

        mentioned_names.append(registry[person_id].name)
    return mentioned_names
