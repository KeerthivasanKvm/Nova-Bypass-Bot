import motor.motor_asyncio
import datetime
import uuid

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.users = self.db.users
        self.links = self.db.links
        self.tokens = self.db.tokens
        self.settings = self.db.settings  # To store banned/allowed sites

    async def add_user(self, user_id):
        user = await self.users.find_one({'_id': user_id})
        if not user:
            await self.users.insert_one({
                '_id': user_id,
                'is_premium': False,
                'premium_expiry': None,
                'daily_usage': 0,
                'last_used_date': datetime.datetime.now().date().isoformat()
            })

    async def get_user(self, user_id):
        return await self.users.find_one({'_id': user_id})

    async def check_link_cache(self, original_link):
        # Look for the link in DB to save processing
        result = await self.links.find_one({'original': original_link})
        return result['bypassed'] if result else None

    async def save_link(self, original, bypassed):
        await self.links.insert_one({'original': original, 'bypassed': bypassed})

    async def update_usage(self, user_id):
        # Resets count if it's a new day
        user = await self.get_user(user_id)
        today = datetime.datetime.now().date().isoformat()
        
        if user['last_used_date'] != today:
            await self.users.update_one({'_id': user_id}, {'$set': {'daily_usage': 1, 'last_used_date': today}})
        else:
            await self.users.update_one({'_id': user_id}, {'$inc': {'daily_usage': 1}})

    # --- Token & Premium Logic ---
    async def generate_token(self, duration_seconds, type="premium"):
        # Type can be "premium" or "reset_limit"
        token = str(uuid.uuid4())[:8]  # Generate short unique token
        await self.tokens.insert_one({
            'token': token,
            'duration': duration_seconds,
            'type': type, 
            'used': False
        })
        return token

    async def redeem_token(self, user_id, token_str):
        token_doc = await self.tokens.find_one({'token': token_str, 'used': False})
        if not token_doc:
            return False, "Invalid or expired token."

        await self.tokens.update_one({'_id': token_doc['_id']}, {'$set': {'used': True}})

        if token_doc['type'] == 'reset_limit':
            await self.users.update_one({'_id': user_id}, {'$set': {'daily_usage': 0}})
            return True, "Daily limit reset successfully!"
            
        elif token_doc['type'] == 'premium':
            # Calculate new expiry
            current_time = datetime.datetime.now()
            expiry = current_time + datetime.timedelta(seconds=token_doc['duration'])
            await self.users.update_one({'_id': user_id}, {
                '$set': {'is_premium': True, 'premium_expiry': expiry}
            })
            return True, f"Premium activated until {expiry}!"

# Initialize in your main file
# db = Database("YOUR_MONGO_URL", "LinkBot")
