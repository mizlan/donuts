"""Event handlers for the Slack donut bot."""

import re
from itertools import combinations
from slack_bolt import App
from better_profanity import profanity

from . import slack_client, tracking, config
from src import history, solver


def register_handlers(app: App) -> None:
    """Register all event handlers with the app."""

    @app.event("app_mention")
    def handle_app_mention(event, client):
        """Respond when the bot is mentioned."""
        channel = event.get("channel")
        ts = event.get("ts")
        thread_ts = event.get("thread_ts")
        text = event.get("text", "")

        # If mentioned in a thread on the parent message with a recovery trigger phrase
        if (
            thread_ts
            and thread_ts != ts
            and re.search(r"try.*again|unacceptable|poop", text, re.IGNORECASE)
        ):
            _recover_single_message(client, channel, thread_ts)
            return

        if profanity.contains_profanity(text):
            image_url = "https://avatars.mds.yandex.net/get-kinopoisk-image/1600647/b19fb75a-b0bd-4949-bf69-9fc6b658e340/3840x"
            alt_text = "uh oh!"
        elif "good boy" in text.lower():
            image_url = "https://i.ytimg.com/vi/cIJd1m2kXMQ/maxresdefault.jpg"
            alt_text = "Good boy Dug!"
        else:
            image_url = "https://i.ytimg.com/vi/1KHSR_Flqww/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLD-pjkiEtODTgatoYJ4KVIa1rgupA"
            alt_text = "Dug!"

        client.chat_postMessage(
            channel=channel,
            thread_ts=ts,
            text="🐕",
            blocks=[
                {
                    "type": "image",
                    "image_url": image_url,
                    "alt_text": alt_text,
                }
            ],
        )

    @app.command("/makedonuts")
    def handle_makedonuts(ack, command, client, say):
        """Generate and post donut pairings."""
        ack()

        try:
            # Load registry and history
            registry = history.parse_registry(config.REGISTRY_PATH)
            past_meetings = history.parse_history(registry, config.HISTORY_PATH)

            # Generate pairings
            pairs = solver.make_assignment(registry, past_meetings)

            # Format message
            text = f"*Generated {len(pairs)} donut chats:*\n"
            for person1, person2 in pairs:
                text += f"• {person1.name} ⋯ {person2.name}\n"

            # Post to the channel where the command was invoked
            channel = command["channel_id"]
            client.chat_postMessage(
                channel=channel, text=text
            )

            print(f"Posted pairings message to {channel}")

        except Exception as e:
            print(f"Error in /makedonuts: {e}")
            say(f"Error generating pairings: {e}")

    @app.event("message")
    def handle_message(event, client, say):
        """Listen for donut chat confirmation messages with @mentions."""
        if not _is_actionable_user_message(event):
            return

        channel = event.get("channel")
        text = event.get("text", "")
        ts = event.get("ts")

        bot_user_id = client.auth_test()["user_id"]
        bot_mentioned = f"<@{bot_user_id}>" in text

        if channel != config.DONUT_CHAT_CHANNEL and not bot_mentioned:
            return

        if event.get("thread_ts") or not text or not ts:
            return

        if not re.findall(r"<@([A-Z0-9]+)>", text):
            return

        try:
            _respond_to_donut_message(client, channel, ts, text)
        except Exception as e:
            print(f"Error in handle_message: {e}")

    @app.command("/recoverdonuts")
    def handle_recoverdonuts(ack, command, client):
        """Recover missed donut chat responses after bot downtime."""
        ack()

        channel = config.DONUT_CHAT_CHANNEL

        try:
            response = client.conversations_history(channel=channel)
            messages = response.get("messages", [])
        except Exception as e:
            print(f"[RECOVER] Error fetching history: {e}")
            client.chat_postMessage(
                channel=command["channel_id"],
                text=f"Error fetching channel history: {e}",
            )
            return

        num_recovered_unprocessed = 0
        num_recovered_unconfirmed = 0
        for message in messages:
            if not _is_actionable_user_message(message):
                continue
            if message.get("thread_ts") and message.get("thread_ts") != message.get("ts"):
                continue

            result = _recover_single_message(client, channel, message=message)
            if result == "unprocessed":
                num_recovered_unprocessed += 1
            elif result == "unconfirmed":
                num_recovered_unconfirmed += 1

        # build channel reply
        reply = "Recovery complete."
        if num_recovered_unprocessed > 0:
            reply += f" Responded to {num_recovered_unprocessed} originally-overlooked message(s)."
        if num_recovered_unconfirmed > 0:
            reply += f" Recorded {num_recovered_unconfirmed} originally-unconfirmed chat(s)."
        client.chat_postMessage(
            channel=command["channel_id"],
            text=reply,
        )

    @app.event("reaction_added")
    def handle_reaction(event, client):
        """Track confirmation when someone reacts with checkmark to donut chat."""
        if event.get("reaction") != "white_check_mark":
            return

        channel = event.get("item", {}).get("channel")
        ts = event.get("item", {}).get("ts")

        if not channel or not ts or channel != config.DONUT_CHAT_CHANNEL:
            return

        if tracking.history_contains_ts(config.HISTORY_PATH, ts):
            return

        try:
            msg_response = client.conversations_history(
                channel=channel, latest=ts, limit=1, inclusive=True
            )
            messages = msg_response.get("messages")
            if not messages:
                return

            _record_donut_confirmation(client, channel, ts, messages[0])
        except Exception as e:
            print(f"Error in handle_reaction: {e}")


def _is_actionable_user_message(message: dict) -> bool:
    """Check if a message is an actionable user message (not bot/system)."""
    if message.get("bot_id"):
        return False
    if message.get("subtype") in ("channel_join", "member_left"):
        return False
    return True


def _respond_to_donut_message(client, channel: str, ts: str, text: str) -> bool:
    """React and reply to a donut chat message if it contains valid mentions.

    Args:
        client: Slack client
        channel: Channel ID
        ts: Message timestamp
        text: Message text

    Returns:
        True if the message was responded to, False otherwise.
    """
    mentions = re.findall(r"<@([A-Z0-9]+)>", text)
    if not mentions:
        return False

    registry = history.parse_registry(config.REGISTRY_PATH)
    identifier_map = _build_identifier_mapping(registry)

    mentioned_names = _get_valid_mentioned_names(
        mentions, client, registry, identifier_map
    )
    if not mentioned_names:
        return False

    client.reactions_add(channel=channel, timestamp=ts, name="white_check_mark")
    _post_confirmation_prompt(client, channel, ts)

    return True


def _post_confirmation_prompt(client, channel: str, ts: str) -> None:
    """Post the 'please react to confirm' thread reply."""
    text = (
        "Please react to this message with :white_check_mark: "
        "to confirm the donut chat happened!"
    )
    client.chat_postMessage(channel=channel, thread_ts=ts, text=text)


def _find_bot_reply(client, channel: str, ts: str) -> dict | None:
    """Find the bot's thread reply for a message.

    Returns:
        The bot's reply message dict, or None if not found.
    """
    try:
        thread_response = client.conversations_replies(
            channel=channel, ts=ts, limit=15
        )
    except Exception as e:
        print(f"Error fetching thread for {ts}: {e}")
        return None

    for thread_msg in thread_response.get("messages", []):
        if thread_msg.get("bot_id") and thread_msg.get("ts") != ts:
            return thread_msg
    return None


def _record_donut_confirmation(
    client, channel: str, ts: str, message: dict
) -> bool:
    """Record a donut chat confirmation from a message.

    Resolves the poster and mentions, records pairs to history,
    strikes through the pairings message, and updates the bot reply.

    Returns:
        True if the confirmation was recorded, False if no valid people found.
    """
    text = message.get("text", "")
    poster_user_id = message.get("user")
    mentions = re.findall(r"<@([A-Z0-9]+)>", text)

    if not mentions or not poster_user_id:
        return False

    poster_email = slack_client.get_user_email(client, poster_user_id)
    if not poster_email:
        return False

    poster_email = _normalize_email(poster_email)

    registry = history.parse_registry(config.REGISTRY_PATH)
    identifier_map = _build_identifier_mapping(registry)

    if poster_email not in identifier_map:
        return False

    poster_name = registry[identifier_map[poster_email]].name

    mentioned_names = _get_valid_mentioned_names(
        mentions, client, registry, identifier_map
    )
    if not mentioned_names:
        return False

    # Record donut chat for each pair
    all_people = [poster_name] + mentioned_names
    pairs = _generate_all_pairs(all_people)
    for person1, person2 in pairs:
        tracking.append_to_history(person1, person2, config.HISTORY_PATH, ts)

    _strikethrough_pair_in_message(client, channel, poster_name, mentioned_names)

    # Update the bot's thread reply
    bot_reply = _find_bot_reply(client, channel, ts)
    if bot_reply:
        client.chat_update(channel=channel, ts=bot_reply["ts"], text="✅ Recorded!")

    return True


def _generate_all_pairs(people: list[str]) -> list[tuple[str, str]]:
    """Generate all unique pairs from a list of people.

    Args:
        people: List of person names

    Returns:
        List of (person1, person2) tuples
    """
    return list(combinations(people, 2))


def _build_identifier_mapping(registry: dict[int, history.Person]) -> dict[str, int]:
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


def _recover_single_message(
    client, channel: str, parent_ts: str | None = None, message: dict | None = None
) -> str | None:
    """Run recovery logic for a single parent message.

    Either parent_ts or message must be provided. If message is given, it is used
    directly; otherwise the message is fetched by parent_ts.

    Returns:
        "unprocessed" if the message was newly responded to,
        "unconfirmed" if a confirmed chat was newly recorded,
        or None if no action was taken.
    """
    bot_user_id = client.auth_test()["user_id"]

    if message is None:
        try:
            response = client.conversations_history(
                channel=channel, latest=parent_ts, limit=1, inclusive=True
            )
            messages = response.get("messages", [])
        except Exception as e:
            print(f"[RECOVER-SINGLE] Error fetching message {parent_ts}: {e}")
            return None

        if not messages:
            return None

        message = messages[0]

    if not _is_actionable_user_message(message):
        return None

    text = message.get("text", "")
    ts = message.get("ts")
    if not text or not ts:
        return None

    reactions = message.get("reactions", [])
    bot_already_reacted = any(
        r.get("name") == "white_check_mark"
        and bot_user_id in r.get("users", [])
        for r in reactions
    )

    if not bot_already_reacted:
        try:
            if _respond_to_donut_message(client, channel, ts, text):
                return "unprocessed"
        except Exception as e:
            print(f"[RECOVER-SINGLE] Error processing message {ts}: {e}")
        return None

    bot_reply = _find_bot_reply(client, channel, ts)

    if bot_reply is None:
        try:
            _post_confirmation_prompt(client, channel, ts)
            return "unprocessed"
        except Exception as e:
            print(f"[RECOVER-SINGLE] Error posting thread reply for {ts}: {e}")
        return None

    if "Recorded" in bot_reply.get("text", ""):
        return None

    user_confirmed = any(
        r.get("name") == "white_check_mark"
        and any(u != bot_user_id for u in r.get("users", []))
        for r in reactions
    )
    if not user_confirmed:
        return None

    if tracking.history_contains_ts(config.HISTORY_PATH, ts):
        try:
            client.chat_update(
                channel=channel, ts=bot_reply["ts"], text="✅ Recorded!"
            )
        except Exception as e:
            print(f"[RECOVER-SINGLE] Error updating bot reply for {ts}: {e}")
        return None

    try:
        if _record_donut_confirmation(client, channel, ts, message):
            return "unconfirmed"
    except Exception as e:
        print(f"[RECOVER-SINGLE] Error processing confirmation for {ts}: {e}")
    return None
