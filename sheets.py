import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import logging
from typing import List, Dict, Optional
import config

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        self.client = None
        self.sheet = None
        self.worksheet = None
        self.connect()

    def connect(self):
        """Connect to Google Sheets"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                config.GOOGLE_SHEETS_CREDENTIALS, scope
            )
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(config.GOOGLE_SHEET_ID)
            
            # Try to get the first worksheet, or create if doesn't exist
            try:
                self.worksheet = self.sheet.get_worksheet(0)
            except:
                self.worksheet = self.sheet.add_worksheet(title="Watchlist", rows="1000", cols="10")
            
            # Initialize headers if sheet is empty
            if not self.worksheet.get_all_values():
                self.worksheet.insert_row(config.STOCK_COLUMNS, 1)
                
            logger.info("Successfully connected to Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise

    def add_stock(self, symbol: str, buy_price: float, target_price: float, 
                  stop_loss: float, notes: str = "") -> bool:
        """Add a new stock to the watchlist"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [
                symbol.upper(),
                buy_price,
                target_price,
                stop_loss,
                0,  # Current price - will be updated by price fetcher
                notes,
                current_time,
                current_time
            ]
            
            self.worksheet.append_row(row_data)
            logger.info(f"Added stock {symbol} to watchlist")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add stock {symbol}: {e}")
            return False

    def remove_stock(self, symbol: str) -> bool:
        """Remove a stock from the watchlist"""
        try:
            symbol = symbol.upper()
            all_records = self.worksheet.get_all_records()
            
            for i, record in enumerate(all_records, start=2):  # Start from row 2 (after header)
                if record['Stock Symbol'] == symbol:
                    self.worksheet.delete_rows(i)
                    logger.info(f"Removed stock {symbol} from watchlist")
                    return True
            
            logger.warning(f"Stock {symbol} not found in watchlist")
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove stock {symbol}: {e}")
            return False

    def get_all_stocks(self) -> List[Dict]:
        """Get all stocks from the watchlist"""
        try:
            records = self.worksheet.get_all_records()
            return records
        except Exception as e:
            logger.error(f"Failed to get stocks: {e}")
            return []

    def update_current_price(self, symbol: str, current_price: float) -> bool:
        """Update the current price of a stock"""
        try:
            symbol = symbol.upper()
            all_records = self.worksheet.get_all_records()
            
            for i, record in enumerate(all_records, start=2):
                if record['Stock Symbol'] == symbol:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.worksheet.update_cell(i, 5, current_price)  # Current Price column
                    self.worksheet.update_cell(i, 8, current_time)   # Last Updated column
                    return True
            
            logger.warning(f"Stock {symbol} not found for price update")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update price for {symbol}: {e}")
            return False

    def get_stock_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Get a specific stock by symbol"""
        try:
            symbol = symbol.upper()
            records = self.get_all_stocks()
            
            for record in records:
                if record['Stock Symbol'] == symbol:
                    return record
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get stock {symbol}: {e}")
            return None

    def bulk_update_prices(self, price_updates: Dict[str, float]) -> bool:
        """Update multiple stock prices at once"""
        try:
            all_records = self.worksheet.get_all_records()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            updates = []
            for i, record in enumerate(all_records, start=2):
                symbol = record['Stock Symbol']
                if symbol in price_updates:
                    updates.append({
                        'range': f'E{i}',  # Current Price column
                        'values': [[price_updates[symbol]]]
                    })
                    updates.append({
                        'range': f'H{i}',  # Last Updated column
                        'values': [[current_time]]
                    })
            
            if updates:
                self.worksheet.batch_update(updates)
                logger.info(f"Updated prices for {len(price_updates)} stocks")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to bulk update prices: {e}")
            return False