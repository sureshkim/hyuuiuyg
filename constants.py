import os
from datetime import datetime
import pytz

# All os.getenv(key, defaultValue) statements will return the value of environmental variable associated with the key
# If no environmental variable is declared with the key as name, defaultValue will be returned
# If defaultValue is not present, then None will be returned
# Go to Azure WebApp > Configuration > Application Settings and define your environmental variables

# Asia/Kolkata Timezone for logging time
TIMEZONE = pytz.timezone('Asia/Kolkata')


# Developer Mode (for Server)
def in_developer_mode() -> bool:
    return os.getenv('DEVELOPER_MODE', 'False').lower() in ['true', '1', 't', 'y']


DEVELOPER_TELEGRAM_USERNAME: str = os.getenv('DEVELOPER_NAME', 'itsyourap')
DEVELOPER_TELEGRAM_LINK: str = os.getenv('DEVELOPER_TELEGRAM', 'https://t.me/itsyourap')
DEVELOPER_TELEGRAM_CHANNEL_ID: str = os.getenv('DEVELOPER_TELEGRAM_CHANNEL_ID')
DEVELOPER_TELEGRAM_CHANNEL_LINK: str = os.getenv('DEVELOPER_TELEGRAM_CHANNEL_LINK')
DEVELOPER_TELEGRAM_CHANNEL_LINK_ESCAPED: str = DEVELOPER_TELEGRAM_CHANNEL_LINK.replace("_", "\\_")

# Webhook Constants
WEBHOOK_HOST = os.getenv('WEBSITE_HOSTNAME')  # Azure Web App has it autoconfigured to its hostname
WEBHOOK_PORT = 443  # 443, 80, 8000, 8080 or 8443 (port needs to be open to the internet)
WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)  # Base URL of the Webhook

# Files and Log Storage Constants
STORAGE_PATH = os.getenv('STORAGE_PATH', os.path.join(os.getcwd(), "files"))  # Main Storage for Program Outputs
DEFAULT_LOG_PATH = os.path.join(STORAGE_PATH, "logs")  # Subdirectory for storing logs
DEFAULT_LOG_FILE_NAME = "log_%s.log" % datetime.now(tz=TIMEZONE).strftime("%d-%m-%Y")  # log_01-01-1970.log


# For customising logging timezone
def timetz(*args):
    return datetime.now(TIMEZONE).timetuple()


# Common function to create directories
def create_directories(directory: str) -> str:
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


create_directories(DEFAULT_LOG_PATH)  # Create the Storage and Logs directory during startup
