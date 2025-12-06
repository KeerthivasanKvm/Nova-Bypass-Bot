import os

# Telegram API credentials (get from my.telegram.org)
API_ID = int(os.environ.get("API_ID", "1234567")) 
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")

# Database (get from mongodb.com)
MONGO_URI = os.environ.get("MONGO_URI", "your_mongodb_connection_string")
DB_NAME = "LinkBypassBot"

# Admin & Channel
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789")) # Your Telegram User ID
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "-100xxxxxxxxx") # Channel ID (must start with -100)

# Settings
FREE_LIMIT = 6  # How many links a free user can convert per day
