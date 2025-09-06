import os
import json
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Google Sheets Configuration
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_SHEETS_CREDENTIALS = json.loads(os.getenv('GOOGLE_SHEETS_CREDENTIALS', '{}'))

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Application Configuration
UPDATE_INTERVAL_MINUTES = 5
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Stock Data Schema
STOCK_COLUMNS = [
    'Stock Symbol',
    'Buy Price',
    'Target Price',
    'Stop Loss',
    'Current Price',
    'Notes',
    'Date Added',
    'Last Updated'
]