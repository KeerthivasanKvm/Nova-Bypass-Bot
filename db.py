import motor.motor_asyncio
import datetime
import uuid
from config import MONGO_URI, DB_NAME, FREE_LIMIT

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.users = self.db.users
        self.links = self.db.links
        self.tokens = self.db.tokens
        self.auth_chats = self.db.auth_chats
        self.banned_sites = self.db.banned_sites

    async def get_user(self, user_id):
        user = await self.users.find_one({'_id': user_id})
        if not user:
            user = {
                '_id': user_id,
                'is_premium': False,
                'premium_expiry': None,
                'daily_usage': 0,
                'last_used': datetime.datetime.now().date().isoformat()
            }
            await self.users.insert_one(user)
        return user

    async def update_usage(self, user_id):
        today = datetime.datetime.now().date().isoformat()
        # Reset count if it's a new day
        await self.users.update_one(
            {'_id': user_id, 'last_used': {'$ne': today}},
            {'$set': {'daily_usage': 0, 'last_used': today}}
        )
        # Increment usage
        await self.users.update_one({'_id': user_id}, {'$inc': {'daily_usage': 1}})

    async def create_token(self, duration, type="premium"):
        token = str(uuid.uuid4())[:8]
        await self.tokens.insert_one({
            'token': token, 'duration': duration, 'type': type, 'used': False
        })
        return token

    async def redeem_token(self, user_id, token_str):
        token_doc = await self.tokens.find_one({'token': token_str, 'used': False})
        if not token_doc: return False, "Invalid or expired token."
        
        await self.tokens.update_one({'_id': token_doc['_id']}, {'$set': {'used': True}})
        
        if token_doc['type'] == 'reset':
            await self.users.update_one({'_id': user_id}, {'$set': {'daily_usage': 0}})
            return True, "Daily limit reset!"
        elif token_doc['type'] == 'premium':
            expiry = datetime.datetime.now() + datetime.timedelta(seconds=token_doc['duration'])
            await self.users.update_one({'_id': user_id}, {'$set': {'is_premium': True, 'premium_expiry': expiry}})
            return True, f"Premium activated until {expiry.strftime('%Y-%m-%d')}!"

    async def authorize_chat(self, chat_id):
        await self.auth_chats.update_one({'_id': chat_id}, {'$set': {'allowed': True}}, upsert=True)

    async def is_authorized(self, chat_id):
        chat = await self.auth_chats.find_one({'_id': chat_id})
        return chat and chat.get('allowed', False)

    async def get_cached_link(self, url):
        res = await self.links.find_one({'original': url})
        return res['bypassed'] if res else None

    async def cache_link(self, original, bypassed):
        await self.links.insert_one({'original': original, 'bypassed': bypassed})

    async def ban_domain(self, domain):
        await self.banned_sites.insert_one({'domain': domain})
    
    async def is_banned(self, url):
        banned = await self.banned_sites.find().to_list(length=None)
        return any(b['domain'] in url for b in banned)

db = Database()
