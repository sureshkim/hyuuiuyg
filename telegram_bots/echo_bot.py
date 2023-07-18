import os
import sys
import time
from abc import ABC
from flask import Flask, request, abort, Response
from telebot import TeleBot
from telebot.types import Message, Update
from telebot.apihelper import ApiTelegramException
from constants import WEBHOOK_URL_BASE, in_developer_mode, DEVELOPER_TELEGRAM_USERNAME, DEVELOPER_TELEGRAM_LINK, \
    DEVELOPER_TELEGRAM_CHANNEL_ID, DEVELOPER_TELEGRAM_CHANNEL_LINK, DEVELOPER_TELEGRAM_CHANNEL_LINK_ESCAPED,\
    timetz, DEFAULT_LOG_PATH, create_directories
from telegram_bots import TelegramBot
import logging.handlers
from concurrent_log_handler import ConcurrentTimedRotatingFileHandler

# Changes Default Logging Timezone
logging.Formatter.converter = timetz

# Creates a logger object which helps in logging requests from users for analytics stuff
logger = logging.getLogger('echo_telegram_bot')

# File logging, rotates file every day at midnight
# (Use ConcurrentTimedRotatingFileHandler since it is a Flask app)
handler = ConcurrentTimedRotatingFileHandler(
    os.path.join(create_directories(os.path.join(DEFAULT_LOG_PATH, "echo_telegram_bot")), "log"),
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
WEB_ROUTE = "/%s" % "echo-bot"

# The Webhook URL - Full URL to the route where Telegram will send POST request
WEBHOOK_URL = WEBHOOK_URL_BASE + WEB_ROUTE

# Bot Token which you get from @BotFather
# Get from https://t.me/BotFather
# Token is saved as an environment variable
# Go to Azure WebApp > Configuration > Application Settings and define your environmental variables
BOT_TOKEN = os.environ.get('ITSYOURAP_ECHO_TELEGRAM_BOT_TOKEN')

# The TeleBot object of the pyTelegramBotAPI library
# This handles everything regarding the bot functions
bot: TeleBot | None = None
if BOT_TOKEN is not None:
    bot = TeleBot(BOT_TOKEN)


# EchoTelegramBot class which extends the TelegramBot class
# Contains all the implementation details for the abstract methods
# Abstract since we do not create objects of this class, instead call the static methods
class EchoTelegramBot(TelegramBot, ABC):
    @staticmethod
    def register_route(flask_app: Flask):
        if bot is not None:
            logger.debug("Adding Route %s", WEB_ROUTE)

            # Add the URL route rule to the Flask Server and associate trigger function on request
            flask_app.add_url_rule(WEB_ROUTE, methods=['POST'], view_func=echo_bot_process_webhook_trigger)

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


def echo_bot_process_webhook_trigger():
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
           "👌 I can echo your text messages\n\n" \
           "😋 Just send me a text and I will send it back to you\n\n" \
           "🔎 GitHub: [Click Here](https://github.com/itsyourap)\n" \
           "🎁 Donate: [UPI](upi://pay?pn=Ankan%20Pal&tn=Donation%20Via%20Telegram%20Bot&pa=itsyourap@oksbi&cu=INR)"

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

    # Echo the sender's message as a reply to their message (The purpose of this bot)
    bot.send_message(message.chat.id, text=message.text, reply_to_message_id=message.message_id,
                     disable_web_page_preview=True)

    # Log the incoming message for analytics purposes
    logger.info("Received Message %s", str({'message': message.json}))
