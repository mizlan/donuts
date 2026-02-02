"""Slack API client and user mapping utilities."""

from slack_bolt.app import App

# Global cache for user info
_user_cache = {}


def build_email_to_slack_id_map(client) -> dict[str, str]:
    """Build mapping from email to Slack user ID.

    Args:
        client: Slack Bolt client

    Returns:
        Dictionary mapping email addresses to Slack user IDs
    """
    global _user_cache

    if _user_cache:
        return _user_cache

    email_map = {}

    try:
        response = client.users_list()
        for user in response.get("members", []):
            email = user.get("profile", {}).get("email")
            if email and not user.get("is_bot"):
                email_map[email] = user["id"]
                _user_cache[email] = user["id"]
    except Exception as e:
        print(f"Error fetching user list: {e}")

    return email_map


def get_user_slack_id(client, email: str) -> str | None:
    """Get Slack user ID from email address.

    Args:
        client: Slack Bolt client
        email: Email address to look up

    Returns:
        Slack user ID or None if not found
    """
    email_map = build_email_to_slack_id_map(client)
    return email_map.get(email)


def get_user_email(client, user_id: str) -> str | None:
    """Get email from Slack user ID.

    Args:
        client: Slack Bolt client
        user_id: Slack user ID

    Returns:
        Email address or None if not found
    """
    try:
        response = client.users_info(user=user_id)
        return response.get("user", {}).get("profile", {}).get("email")
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return None


def get_user_info(client, user_id: str) -> dict | None:
    """Get user info from Slack user ID.

    Args:
        client: Slack Bolt client
        user_id: Slack user ID

    Returns:
        Dictionary with email and real_name, or None if not found
    """
    try:
        response = client.users_info(user=user_id)
        user = response.get("user", {})
        return {
            "email": user.get("profile", {}).get("email"),
            "real_name": user.get("real_name"),
        }
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return None
