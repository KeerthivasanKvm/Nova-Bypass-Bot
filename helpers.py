import cloudscraper
from pyrogram.errors import UserNotParticipant
from config import FORCE_SUB_CHANNEL

# Cloudflare Scraper
scraper = cloudscraper.create_scraper(browser='chrome')

def cloudflare_bypass(url):
    try:
        response = scraper.get(url, allow_redirects=True)
        if response.status_code == 200:
            return response.url
    except Exception as e:
        print(f"Cloudflare Error: {e}")
    return None

async def check_force_sub(client, user_id):
    if not FORCE_SUB_CHANNEL: return True
    try:
        await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True 
