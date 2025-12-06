import os

API_ID = int(os.environ.get("API_ID", "12345"))
API_HASH = os.environ.get("API_HASH", "your_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

# Database
MONGO_URI = os.environ.get("MONGO_URI", "your_mongodb_connection_string")
DB_NAME = "LinkBypassBot"

# Admin & Permissions
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "-1001234567890") # ID of your channel
AUTH_GROUP_ONLY = True # If True, bot ignores PMs unless whitelisted

# Limits
FREE_LIMIT = 6
