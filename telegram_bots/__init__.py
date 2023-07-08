from abc import ABC, abstractmethod
from flask import Flask


# Common abstract class containing method skeleton for all TelegramBots
# Every TelegramBot should extend this class and implement the methods.
# The methods will be called in sequential order as declared here
class TelegramBot(ABC):
    # Implement this to register the route for the webhook URL
    # Telegram will send POST request to this route of this server when your bot receives a message
    @staticmethod
    @abstractmethod
    def register_route(flask_app: Flask):
        pass

    # Implement this to register the webhook of the bot with Telegram API
    @staticmethod
    @abstractmethod
    def register_webhook():
        pass
