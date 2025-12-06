from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    Message,
)
from os import environ, remove
from threading import Thread
from json import load
from re import search
import re
from urlextract import URLExtract
from texts import HELP_TEXT
import bypasser
import freewall
from time import time
from db import DB

# In main.py
from pyrogram import Client, filters
from db import Database
import time

# Bot configuration
with open("config.json", "r") as f:
    DATA: dict = load(f)


# Helper to parse time (e.g., "1d", "1h")
def parse_duration(time_str):
    unit = time_str[-1]
    value = int(time_str[:-1])
    if unit == 'h': return value * 3600
    if unit == 'd': return value * 86400
    if unit == 'm': return value * 2592000 # 30 days
    return 0

ADMIN_ID = getenv("ADMIN_IDS")  # Replace with your ID
FREE_LIMIT = 6 # How many links free users can do

@app.on_message(filters.command("generate") & filters.user(ADMIN_ID))
async def generate_access(client, message):
    # Usage: /generate 1d premium  OR /generate 0 reset
    try:
        args = message.command
        duration_str = args[1]
        token_type = args[2] if len(args) > 2 else "premium"
        
        seconds = parse_duration(duration_str) if token_type == "premium" else 0
        
        token = await db.generate_token(seconds, type=token_type)
        await message.reply_text(f"Generated Token:\n`{token}`\nType: {token_type}\nDuration: {duration_str}")
    except Exception as e:
        await message.reply_text("Usage: /generate 1d premium OR /generate 1 reset")

@app.on_message(filters.command("redeem"))
async def redeem_access(client, message):
    token = message.command[1]
    success, msg = await db.redeem_token(message.from_user.id, token)
    await message.reply_text(msg)


# Initialize URL extractor
extractor = URLExtract()

@app.on_message(filters.text)
async def handle_link(client, message):
    user_id = message.from_user.id
    url = message.text.strip()

    # 1. Ensure user exists in DB
    await db.add_user(user_id)
    user = await db.get_user(user_id)

    # 2. Check Premium Status & Expiry
    is_premium = user['is_premium']
    if is_premium and user['premium_expiry']:
        if datetime.datetime.now() > user['premium_expiry']:
            is_premium = False # Expired
            # You might want to update DB here to set is_premium=False

    # 3. Check Limits for Free Users
    if not is_premium:
        if user['daily_usage'] >= FREE_LIMIT:
            await message.reply_text(
                "❌ **Daily Limit Reached**\n\n"
                "You have used your free bypasses for today.\n"
                "Buy a Premium Token or use a Reset Key to continue.\n"
                "Use `/redeem <token>`"
            )
            return

    # 4. Check Cache (Optimization)
    cached_link = await db.check_link_cache(url)
    if cached_link:
        await message.reply_text(f"✅ Cached Result: {cached_link}")
        return

    # 5. Domain Blocking/Allowing (Admin restriction)
    # Fetch banned domains from DB (you need to implement the settings collection)
    settings = await db.settings.find_one({'_id': 'main_settings'})
    if settings and any(banned in url for banned in settings.get('banned_domains', [])):
        await message.reply_text("❌ This website is restricted by Admin.")
        return

    # 6. Proceed to Bypass (Cloudflare compatible)
    msg = await message.reply_text("🔎 Bypassing...")
    try:
        # CALL YOUR BYPASSER FUNCTION HERE
        result_link = bypasser_logic(url) 
        
        if result_link:
            # Save to Cache
            await db.save_link(url, result_link)
            # Increment Usage
            await db.update_usage(user_id)
            
            await msg.edit_text(f"✅ Bypassed: {result_link}")
        else:
            await msg.edit_text("❌ Failed to bypass.")
            
    except Exception as e:
        await msg.edit_text(f"Error: {e}")

def getenv(var):
    return environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
with app:
    app.set_bot_commands(
        [
            BotCommand("start", "Welcome Message"),
            BotCommand("help", "List of All Supported Sites"),
        ]
    )

# Database setup
db_api = getenv("DB_API")
db_owner = getenv("DB_OWNER")
db_name = getenv("DB_NAME")
try:
    database = DB(api_key=db_api, db_owner=db_owner, db_name=db_name)
except:
    print("Database is Not Set")
    database = None

# Handle index
def handleIndex(ele: str, message: Message, msg: Message):
    result = bypasser.scrapeIndex(ele)
    try:
        app.delete_messages(message.chat.id, msg.id)
    except:
        pass
    if database and result:
        database.insert(ele, result)
    for page in result:
        app.send_message(
            message.chat.id,
            page,
            reply_to_message_id=message.id,
            disable_web_page_preview=True,
        )

# URL regex pattern
URL_REGEX = r'(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+'

# Updated loopthread function
def loopthread(message: Message, otherss=False):
    urls = []
    # Use message.caption for media (otherss=True), message.text for text messages (otherss=False)
    if otherss:
        texts = message.caption or ""
    else:
        texts = message.text or ""

    # Check entities based on message type
    entities = []
    if otherss and hasattr(message, 'caption_entities') and message.caption_entities:
        entities = message.caption_entities
    elif message.entities:
        entities = message.entities

    # Step 1: Extract URLs from entities
    if entities:
        for entity in entities:
            entity_type = str(entity.type)
            normalized_type = entity_type.split('.')[-1].lower() if '.' in entity_type else entity_type.lower()
            
            if normalized_type == "url":
                url = texts[entity.offset:entity.offset + entity.length]
                urls.append(url)
            elif normalized_type == "text_link":
                if hasattr(entity, 'url') and entity.url:
                    urls.append(entity.url)

    # Step 2: Fallback to text-based URL extraction
    extracted_urls = extractor.find_urls(texts)
    urls.extend(extracted_urls)
    regex_urls = re.findall(URL_REGEX, texts)
    urls.extend(regex_urls)

    # Step 3: Clean and deduplicate URLs
    cleaned_urls = []
    for url in urls:
        cleaned_url = url.strip(".,").rstrip("/")
        if cleaned_url:
            cleaned_urls.append(cleaned_url)
    urls = list(dict.fromkeys(cleaned_urls))  # Preserve order, remove duplicates
    if not urls:
        app.send_message(
            message.chat.id,
            "No valid URLs found in the message.",
            reply_to_message_id=message.id
        )
        return

    # Step 4: Normalize URLs (add protocol if missing)
    normalized_urls = []
    for url in urls:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        normalized_urls.append(url)
    urls = normalized_urls

    # Bypassing logic
    if bypasser.ispresent(bypasser.ddl.ddllist, urls[0]):
        msg: Message = app.send_message(
            message.chat.id, "⚡ __generating...__", reply_to_message_id=message.id
        )
    elif freewall.pass_paywall(urls[0], check=True):
        msg: Message = app.send_message(
            message.chat.id, "🕴️ __jumping the wall...__", reply_to_message_id=message.id
        )
    else:
        if "https://olamovies" in urls[0] or "https://psa.wf/" in urls[0]:
            msg: Message = app.send_message(
                message.chat.id,
                "⏳ __this might take some time...__",
                reply_to_message_id=message.id,
            )
        else:
            msg: Message = app.send_message(
                message.chat.id, "🔎 __bypassing...__", reply_to_message_id=message.id
            )

    strt = time()
    links = ""
    temp = None

    for ele in urls:
        if database:
            df_find = database.find(ele)
        else:
            df_find = None
        if df_find:
            print("Found in DB")
            temp = df_find
        elif search(r"https?:\/\/(?:[\w.-]+)?\.\w+\/\d+:", ele):
            handleIndex(ele, message, msg)
            return
        elif bypasser.ispresent(bypasser.ddl.ddllist, ele):
            try:
                temp = bypasser.ddl.direct_link_generator(ele)
            except Exception as e:
                temp = "**Error**: " + str(e)
        elif freewall.pass_paywall(ele, check=True):
            freefile = freewall.pass_paywall(ele)
            if freefile:
                try:
                    app.send_document(
                        message.chat.id, freefile, reply_to_message_id=message.id
                    )
                    remove(freefile)
                    app.delete_messages(message.chat.id, [msg.id])
                    return
                except:
                    pass
            else:
                app.send_message(
                    message.chat.id, "__Failed to Jump", reply_to_message_id=message.id
                )
        else:
            try:
                temp = bypasser.shortners(ele)
            except Exception as e:
                temp = "**Error**: " + str(e)

        print("bypassed:", temp)
        if temp is not None:
            if (not df_find) and ("http://" in temp or "https://" in temp) and database:
                print("Adding to DB")
                database.insert(ele, temp)
            links = links + temp + "\n"

    end = time()
    print("Took " + "{:.2f}".format(end - strt) + "sec")

    # Send bypassed links
    try:
        final = []
        tmp = ""
        for ele in links.split("\n"):
            tmp += ele + "\n"
            if len(tmp) > 4000:
                final.append(tmp)
                tmp = ""
        final.append(tmp)
        app.delete_messages(message.chat.id, msg.id)
        tmsgid = message.id
        for ele in final:
            tmsg = app.send_message(
                message.chat.id,
                f"__{ele}__",
                reply_to_message_id=tmsgid,
                disable_web_page_preview=True,
            )
            tmsgid = tmsg.id
    except Exception as e:
        app.send_message(
            message.chat.id,
            f"__Failed to Bypass : {e}__",
            reply_to_message_id=message.id,
        )

# Start command
@app.on_message(filters.command(["start"]))
def send_start(client: Client, message: Message):
    app.send_message(
        message.chat.id,
        f"__👋 Hi **{message.from_user.mention}**, I am Link Bypasser Bot, just send me any supported links and I will get you results.\nCheckout /help to Read More__",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🌐 Source Code",
                        url="https://github.com/bipinkrish/Link-Bypasser-Bot",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Replit",
                        url="https://replit.com/@bipinkrish/Link-Bypasser#app.py",
                    )
                ],
            ]
        ),
        reply_to_message_id=message.id,
    )

# Help command
@app.on_message(filters.command(["help"]))
def send_help(client: Client, message: Message):
    app.send_message(
        message.chat.id,
        HELP_TEXT,
        reply_to_message_id=message.id,
        disable_web_page_preview=True,
    )

# Text message handler
@app.on_message(filters.text)
def receive(client: Client, message: Message):
    bypass = Thread(target=lambda: loopthread(message), daemon=True)
    bypass.start()

# Document thread for DLC files
def docthread(message: Message):
    msg: Message = app.send_message(
        message.chat.id, "🔎 __bypassing...__", reply_to_message_id=message.id
    )
    print("sent DLC file")
    file = app.download_media(message)
    dlccont = open(file, "r").read()
    links = bypasser.getlinks(dlccont)
    app.edit_message_text(
        message.chat.id, msg.id, f"__{links}__", disable_web_page_preview=True
    )
    remove(file)

# Media file handler
@app.on_message([filters.document, filters.photo, filters.video])
def docfile(client: Client, message: Message):
    try:
        if message.document and message.document.file_name.endswith("dlc"):
            bypass = Thread(target=lambda: docthread(message), daemon=True)
            bypass.start()
            return
    except:
        pass
    bypass = Thread(target=lambda: loopthread(message, True), daemon=True)
    bypass.start()

# Start the bot
print("Bot Starting")
app.run()



