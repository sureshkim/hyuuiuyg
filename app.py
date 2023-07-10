import os
from flask import Flask, Response, render_template, send_from_directory
from typing import Type
from constants import DEVELOPER_MODE, WEBHOOK_HOST
from telegram_bots import TelegramBot
from telegram_bots.echo_bot import EchoTelegramBot
from telegram_bots.gplinks_bypasser_telegram_bot import GpLinksBypasserTelegramBot

# The Flask App object
app = Flask(__name__)


# The root route of your website
# Returns content of index.html after rendering with Jinja2
@app.route('/')
def index():
    return render_template("index.html")


# Returns the favicon for the website
# Used in the root index.html page
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


# Keep Alive Route
# Azure turns-off the webapp after some time if it does not receive any requests for the time
# Requests to this route frequently will keep the webapp alive
# You can use https://cron-job.org/ to automate the requests at every specified time interval
@app.route('/keep-alive')
def keep_alive():
    # Returns 204 No Content since response is not required for keep-alive
    # The shorter the response, the faster will be the keep-alive script
    return Response(status=204)


# 1. Registers the route for webhook in this server
# 2. Registers the webhook for the bot on Telegram
def initialize_telegram_bots():
    # Add the Telegram Bots here
    # If you are in developer mode, then only the first bot will run
    # Only one bot is intended to be tested on developer mode
    telegram_bots: list[Type[TelegramBot]] = [
        EchoTelegramBot,
        GpLinksBypasserTelegramBot
    ]

    # Enable Bots for Development Server
    if DEVELOPER_MODE:
        # Only One Bot Should Be Present on Dev Server
        # Deletes all the Telegram Bots in the array except the first one
        del telegram_bots[1:]

    # Loop through all the bots and initialize them
    for telegram_bot in telegram_bots:
        telegram_bot.register_route(flask_app=app)
        telegram_bot.register_webhook()


# If this is not an Azure Web App Environment, then don't run the bots
# If you want to run locally, you need to have a port exposed to the internet
# Define the exposed hostname/IP and port in constants.py
if WEBHOOK_HOST is not None:
    # Initialize all the Telegram Bots one by one before Flask Server startup
    # Since gunicorn is used on Azure Web App, __main__ isn't run
    initialize_telegram_bots()
