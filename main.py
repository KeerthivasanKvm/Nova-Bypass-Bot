from pyrogram import Client, filters, enums
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, FREE_LIMIT, FORCE_SUB_CHANNEL
from database import db
from helpers import check_force_sub, cloudflare_bypass
import datetime
# Import your old bypasser functions if needed
# from bypasser import bypass_adfly (example)

app = Client("LinkBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- MIDDLEWARE (Auth & Force Sub) ---
@app.on_message(filters.text & ~filters.user(ADMIN_ID), group=-1)
async def middleware(client, message):
    if message.chat.type == enums.ChatType.PRIVATE:
        # Private Message: Check if User is Authorized (or just allow PMs if you prefer)
        if not await db.is_authorized(message.chat.id):
             # Uncomment below if you want to strictly block PMs unless authorized
             # await message.reply("⛔ You are not authorized. Contact Admin.")
             # message.stop_propagation()
             pass 
    else:
        # Group Message: Check if Group is Authorized
        if not await db.is_authorized(message.chat.id):
            message.stop_propagation()

    # Check Force Join
    if not await check_force_sub(client, message.from_user.id):
        try:
            invite = await client.export_chat_invite_link(FORCE_SUB_CHANNEL)
            await message.reply(f"⚠ **Join First:** [Channel Link]({invite})", disable_web_page_preview=True)
        except:
            await message.reply("⚠ Join the update channel first.")
        message.stop_propagation()

# --- ADMIN COMMANDS ---
@app.on_message(filters.command("auth") & filters.user(ADMIN_ID))
async def auth_chat(c, m):
    # Use: /auth in a group, or /auth <id>
    chat_id = m.chat.id
    if len(m.command) > 1: chat_id = int(m.command[1])
    await db.authorize_chat(chat_id)
    await m.reply(f"✅ ID `{chat_id}` is now authorized.")

@app.on_message(filters.command("ban") & filters.user(ADMIN_ID))
async def ban_site(c, m):
    if len(m.command) > 1:
        await db.ban_domain(m.command[1])
        await m.reply(f"🚫 {m.command[1]} banned.")

@app.on_message(filters.command("generate") & filters.user(ADMIN_ID))
async def generate(c, m):
    # /generate 1d premium  OR /generate 0 reset
    try:
        time_s = m.command[1]
        type_s = m.command[2] if len(m.command) > 2 else "premium"
        duration = 0
        if "d" in time_s: duration = int(time_s.replace("d","")) * 86400
        elif "h" in time_s: duration = int(time_s.replace("h","")) * 3600
        
        token = await db.create_token(duration, type_s)
        await m.reply(f"🎟 **Token:** `{token}`\nType: {type_s}")
    except: await m.reply("Usage: `/generate 1d premium`")

# --- USER COMMANDS ---
@app.on_message(filters.command("redeem"))
async def redeem(c, m):
    if len(m.command) > 1:
        res, text = await db.redeem_token(m.from_user.id, m.command[1])
        await m.reply(text)
    else: await m.reply("Usage: `/redeem <token>`")

@app.on_message(filters.command("start"))
async def start(c, m):
    await m.reply(f"👋 Welcome! I am a Link Bypasser.\n\n**Free Limit:** {FREE_LIMIT}/day\n**Status:** /myplan")

@app.on_message(filters.command("myplan"))
async def myplan(c, m):
    user = await db.get_user(m.from_user.id)
    status = "Premium 🌟" if user['is_premium'] else "Free 👤"
    expiry = user['premium_expiry'] if user['is_premium'] else "Never"
    await m.reply(f"**Plan:** {status}\n**Expiry:** {expiry}\n**Used Today:** {user['daily_usage']}/{FREE_LIMIT}")

# --- BYPASS HANDLER ---
@app.on_message(filters.regex(r'http[s]?://'))
async def bypass_handler(c, m):
    url = m.text.strip()
    user_id = m.from_user.id
    user = await db.get_user(user_id)

    # Check Premium/Limits
    is_prem = user['is_premium']
    if is_prem and user['premium_expiry'] and datetime.datetime.now() > user['premium_expiry']:
        is_prem = False
    
    if not is_prem and user['daily_usage'] >= FREE_LIMIT:
        return await m.reply("❌ **Limit Reached.** Buy Premium or use `/redeem` with a reset key.")

    if await db.is_banned(url): return await m.reply("❌ Website blocked.")

    # Check Cache
    cached = await db.get_cached_link(url)
    if cached:
        await db.update_usage(user_id)
        return await m.reply(f"✅ **Bypassed (Cached):**\n{cached}", disable_web_page_preview=True)

    # Bypass Logic
    msg = await m.reply("🔎 **Bypassing...**")
    try:
        final_link = cloudflare_bypass(url)
        # IF cloudflare fails, add logic here to call your old bypasser.py functions
        
        if final_link:
            await db.cache_link(url, final_link)
            await db.update_usage(user_id)
            await msg.edit(f"✅ **Bypassed:**\n{final_link}", disable_web_page_preview=True)
        else:
            await msg.edit("❌ Failed. Website might be unsupported.")
    except Exception as e:
        await msg.edit(f"Error: {e}")

if __name__ == "__main__":
    app.run()
