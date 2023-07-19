import os
import sys
import time
from abc import ABC
import cloudscraper
import validators
from bs4 import BeautifulSoup
from flask import Flask, request, abort, Response
from telebot import TeleBot
from telebot.types import Message, Update
from telebot.apihelper import ApiTelegramException
from constants import WEBHOOK_URL_BASE, in_developer_mode, DEVELOPER_TELEGRAM_USERNAME, DEVELOPER_TELEGRAM_LINK, \
    DEVELOPER_TELEGRAM_CHANNEL_ID, DEVELOPER_TELEGRAM_CHANNEL_LINK, DEVELOPER_TELEGRAM_CHANNEL_LINK_ESCAPED, \
    timetz, DEFAULT_LOG_PATH, create_directories
from telegram_bots import TelegramBot
import logging.handlers
from concurrent_log_handler import ConcurrentTimedRotatingFileHandler

# Changes Default Logging Timezone
logging.Formatter.converter = timetz

# Creates a logger object which helps in logging requests from users for analytics stuff
logger = logging.getLogger('gplinks_bypasser_telegram_bot')

# File logging, rotates file every day at midnight
# (Use ConcurrentTimedRotatingFileHandler since it is a Flask app)
handler = ConcurrentTimedRotatingFileHandler(
    os.path.join(create_directories(os.path.join(DEFAULT_LOG_PATH, "gplinks_bypasser_telegram_bot")), "log"),
    when='midnight', interval=1
)

# File Suffix for every rotation of log file
handler.suffix = "%d-%m-%Y"

# File Logging Handler Log Format
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

# Add the file logging handler to the logger
logger.addHandler(handler)

# Add logging handler to print logs to stdout
# (You can remove this line if you don't require this)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Sets Log Level
# (See https://docs.python.org/3/howto/logging.html#when-to-use-logging)
logger.setLevel(logging.DEBUG)

# The route at which Flask will listen to.
# Whenever a message is received by the Telegram Bot, Telegram sends a POST request to this route
WEB_ROUTE = "/%s" % "gp-link-bypass"

# The Webhook URL - Full URL to the route where Telegram will send POST request
WEBHOOK_URL = WEBHOOK_URL_BASE + WEB_ROUTE

# Bot Token which you get from @BotFather
# Get from https://t.me/BotFather
# Token is saved as an environment variable
# Go to Azure WebApp > Configuration > Application Settings and define your environmental variables
BOT_TOKEN = os.environ.get('ITSYOURAP_GPLINK_BYPASSER_TELEGRAM_BOT_TOKEN')

# The TeleBot object of the pyTelegramBotAPI library
# This handles everything regarding the bot functions
bot: TeleBot | None = None
if BOT_TOKEN is not None:
    bot = TeleBot(BOT_TOKEN)


# GpLinksBypasserTelegramBot class which extends the TelegramBot class
# Contains all the implementation details for the abstract methods
# Abstract since we do not create objects of this class, instead call the static methods
class GpLinksBypasserTelegramBot(TelegramBot, ABC):
    @staticmethod
    def register_route(flask_app: Flask):
        if bot is not None:
            logger.debug("Adding Route %s", WEB_ROUTE)

            # Add the URL route rule to the Flask Server and associate trigger function on request
            flask_app.add_url_rule(WEB_ROUTE, methods=['POST'], view_func=gp_link_bypass_process_webhook_trigger)

    @staticmethod
    def register_webhook():
        if bot is not None:
            logger.debug("Registering Webhook at %s", WEBHOOK_URL)

            # Register Webhook at Telegram for the Telegram Bot
            set_webhook(WEBHOOK_URL)


def set_webhook(url):
    # Remove any existing webhook
    bot.remove_webhook()

    # Wait some time before assigning the new webhook
    time.sleep(0.1)

    # Assign the new webhook to url
    bot.set_webhook(url=url)


def gp_link_bypass_process_webhook_trigger():
    if request.headers.get('Content-Type') == 'application/json':
        # Get the Webhook POST data
        json_string = request.get_data().decode('utf-8')

        # De-serialize the JSON POST data to Telebot Message
        update = Update.de_json(json_string)

        # Handle the new message
        bot.process_new_updates([update])

        # Message handled successfully, now return 204 No Content
        return Response(status=204)
    else:
        # Telegram did not trigger the Webhook, abort with 403 Forbidden
        abort(403)


# Handle /start and /help messages sent to the Telegram bot
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: Message):
    # Reply message to /start and /help
    text = f"😃 **Hi [{message.chat.first_name}](https://t.me/{message.chat.username}),**\n\n" \
           "👌 I can bypass gplinks.co URLs in few seconds\n\n" \
           "😋 Just send me an URL in https://gplinks.co/xxx format\n\n" \
           "🧑🏻‍💻 Created by [@itsyourap](https://t.me/itsyourap)\n" \
           "🔎 GitHub: [Click Here](https://github.com/itsyourap)\n" \
           "🎁 Donate: UPI - `itsyourap@oksbi`"

    # If this server is marked as Development Server then only reply to developer (owner)
    if in_developer_mode():
        text = text + f"\n\n" \
                      "⚙️ Currently I am in Developer Mode\n" \
                      f"🫡 I will only respond to [@{DEVELOPER_TELEGRAM_USERNAME}]({DEVELOPER_TELEGRAM_LINK})"

    # Send the message as a reply to the sender's message
    bot.send_message(message.chat.id, text=text, reply_to_message_id=message.message_id, parse_mode='Markdown',
                     disable_web_page_preview=True)

    # Log the incoming message for analytics purposes
    logger.info("Received /start through %s", message.json)


# Handle any incoming message sent to the Telegram bot
@bot.message_handler(func=lambda msg: True)
def echo_all(message: Message):
    # If this server is marked as Development Server then only reply to developer (owner)
    if in_developer_mode():
        # Message Sender isn't developer (owner)
        if message.chat.username != DEVELOPER_TELEGRAM_USERNAME:
            # Inform that bot only replies to developer (owner) as a reply to the sender's message
            text = "⚙️ Currently I am in Developer Mode\n" \
                   f"🫡 I will only respond to [@{DEVELOPER_TELEGRAM_USERNAME}]({DEVELOPER_TELEGRAM_LINK})"
            bot.send_message(message.chat.id, text=text, reply_to_message_id=message.message_id,
                             disable_web_page_preview=True)

            # Log request made by sender other than developer for analytics purposes
            logger.info("Received Message From Non-Dev %s", str({'message': message.json}))
            return

    # Check if Developer's Telegram Channel is defined in constants.py
    # If yes, then check if user is subscribed to the channel
    # If user is not subscribed to the channel, ask them to subscribe for the bot to work for them
    # If the user is already subscribed to the channel, then do the actual purpose of the bot
    if DEVELOPER_TELEGRAM_CHANNEL_ID is not None:
        try:
            # Check if user is already subscribed to the Developer's Telegram Channel
            # For this to work, you need to add this bot as an Admin of the Channel
            bot.get_chat_member(chat_id=DEVELOPER_TELEGRAM_CHANNEL_ID, user_id=message.chat.id)

            # User is already subscribed to the Developer's Telegram Channel
            pass
        except ApiTelegramException:
            # User is not subscribed to the Developer's Telegram Channel
            # Ask them to subscribe
            text = f"**Join [this channel]({DEVELOPER_TELEGRAM_CHANNEL_LINK}) to use this bot**\n" \
                   f"{DEVELOPER_TELEGRAM_CHANNEL_LINK_ESCAPED}"
            bot.send_message(message.chat.id, text=text, reply_to_message_id=message.message_id,
                             disable_web_page_preview=True, parse_mode='Markdown')

            # Log the incoming message for analytics purposes
            logger.info("Received Message from unsubscribed user %s", str({'message': message.json}))
            return

    # Inform the sender that bot is online and has received their message
    processing_msg = bot.reply_to(message, "Processing... Please Wait")

    # Bypass the gplinks.co URL and get the bypassed URL
    bypassed_url = gplinks_bypasser_handle_request(message.text)

    # Delete the 'Processing...' message
    bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)

    # Reply to the sender's gplinks.co URL with the bypassed URL
    bot.reply_to(message, bypassed_url)

    # Log the incoming message and bypassed URL for analytics purposes
    logger.info("Received Message %s", str({'message': message.json, 'bypassed_url': bypassed_url}))


def gplinks_bypass(url: str):
    try:
        # Since only cloudscraper can bypass Cloudflare bot detection
        client = cloudscraper.create_scraper(allow_brotli=False)

        # Visitor ID provided by GPLinks that stores the session
        vid = client.get(url, allow_redirects=False).headers["Location"].split("=")[-1]

        # Convince GPLink that visitor has already visited the 3rd ads page and clicked continue
        for i in range(2):
            client.post(url="https://gplinks.in/track/data.php",
                        data={"request": "addVisitorImps", "vid": vid})

        client.post(url="https://gplinks.in/track/data.php",
                    data={"request": "setVisitor", "vid": vid, "status": 3})

        # Request to get the final GPLink verification page
        go_url = f"{url}/?vid={vid}"
        response = client.get(go_url, allow_redirects=False)
        soup = BeautifulSoup(response.content, "html.parser")

        data = {}

        # Find the final GPLink verification page link in the webpage
        go_link_form = soup.find_all(id="go-link")
        for form_elem in go_link_form:
            if form_elem is not None:
                inputs = form_elem.find_all("input")
                for input_elem in inputs:
                    data[input_elem.get('name')] = input_elem.get('value')

        # GPLinks doesn't provide the actual link if the requests are too fast
        time.sleep(1)

        # Final request to get the actual bypassed link
        bypassed_url = client.post(url="https://gplinks.co/links/go",
                                   data=data,
                                   headers={"x-requested-with": "XMLHttpRequest"}
                                   ).json()["url"]
        return bypassed_url
    except Exception as ex:
        logger.error(ex)
        return None


def gplinks_bypasser_handle_request(url: str):
    # Malformed URL
    if not validators.url(url):
        return "Malformed URL"

    # URL provided is not a gplinks.co URL
    if "gplinks.co/" not in url:
        return "Invalid URL\n" \
               "Please send your URL in https://gplinks.co/xxx format"

    bypass = ""
    count = 1

    # Loop at least 10 times because a lot of times the link is None
    while bypass is None or bypass == "":
        if count >= 10:
            # Couldn't bypass the URL
            return "Error"

        # Try to bypass the URL
        bypass = gplinks_bypass(url)
        count += 1
    return bypass
