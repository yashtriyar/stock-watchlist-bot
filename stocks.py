import requests
from bs4 import BeautifulSoup
import pandas as pd
import ta
from typing import Dict, List, Optional
import logging
from datetime import datetime
import time
import re
import investpy
import yfinance as yf  # Only for historical data

logger = logging.getLogger(__name__)

class StockAnalyzer:
    def __init__(self):
        self.cache = {}
        
    def get_stock_price(self, symbol: str) -> Optional[float]:
        """
        Fetch Indian stock price with multiple fallbacks:
        1. NSE API
        2. Google Finance
        3. Moneycontrol
        """
        symbol = symbol.upper().replace('.NS', '').replace('.BO', '')
        
        # Check cache (5-minute cache)
        cache_key = f"{symbol}_{int(time.time() // 300)}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # ---------------- NSE API ----------------
        try:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
            }
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=10)
            data = response.json()
            price = float(data["priceInfo"]["lastPrice"])
            
            # Cache and return
            self.cache[cache_key] = price
            logger.info(f"NSE: {symbol} = ₹{price}")
            return price
            
        except Exception as e:
            logger.debug(f"NSE failed for {symbol}: {e}")

        # ---------------- Google Finance ----------------
        try:
            url = f"https://www.google.com/finance/quote/{symbol}:NSE"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            price_tag = soup.find("div", class_="YMlKec fxKbKc")
            if price_tag:
                price_text = price_tag.text.replace(",", "").replace("₹", "").strip()
                price = float(price_text)
                
                # Cache and return
                self.cache[cache_key] = price
                logger.info(f"Google Finance: {symbol} = ₹{price}")
                return price
                
        except Exception as e:
            logger.debug(f"Google Finance failed for {symbol}: {e}")

        # ---------------- Moneycontrol ----------------
        try:
            url = f"https://www.moneycontrol.com/india/stockpricequote/{symbol.lower()}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            price_tag = soup.find("div", {"id": "Nse_Prc_tick"})
            if price_tag:
                price = float(price_tag.text.strip().replace(",", ""))
                
                # Cache and return
                self.cache[cache_key] = price
                logger.info(f"Moneycontrol: {symbol} = ₹{price}")
                return price
                
        except Exception as e:
            logger.debug(f"Moneycontrol failed for {symbol}: {e}")

        logger.warning(f"All sources failed for {symbol}")
        return None

    def bulk_get_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get prices for multiple stocks"""
        prices = {}
        for symbol in symbols:
            price = self.get_stock_price(symbol)
            if price:
                prices[symbol] = price
            time.sleep(1)  # Rate limiting
        return prices

    

    def get_historical_data(self, symbol: str, period: str = "3mo") -> Optional[pd.DataFrame]:
        """Get historical data using investpy (instead of yfinance)"""
        try:
            # Map period to actual date ranges
            period_map = {
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365
            }
            days = period_map.get(period, 90)

            # Fetch data from NSE
            data = investpy.get_stock_historical_data(
                stock=symbol,
                country="India",
                from_date=(datetime.now() - pd.Timedelta(days=days)).strftime("%d/%m/%Y"),
                to_date=datetime.now().strftime("%d/%m/%Y")
            )

            return data if not data.empty else None

        except Exception as e:
            logger.error(f"Historical data failed for {symbol}: {e}")
            return None
    
    
    def calculate_technical_indicators(self, symbol: str) -> Dict:
        """Calculate technical indicators"""
        try:
            data = self.get_historical_data(symbol)
            if data is None or len(data) < 50:
                return {}

            indicators = {}
            
            # RSI
            indicators['rsi'] = ta.momentum.RSIIndicator(close=data['Close']).rsi().iloc[-1]
            
            # MACD
            macd = ta.trend.MACD(close=data['Close'])
            indicators['macd'] = macd.macd().iloc[-1]
            indicators['macd_signal'] = macd.macd_signal().iloc[-1]
            
            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(close=data['Close'])
            indicators['bb_upper'] = bollinger.bollinger_hband().iloc[-1]
            indicators['bb_lower'] = bollinger.bollinger_lband().iloc[-1]
            current_price = data['Close'].iloc[-1]
            indicators['bb_position'] = (current_price - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
            
            # Moving Averages
            indicators['ema_50'] = ta.trend.EMAIndicator(close=data['Close'], window=50).ema_indicator().iloc[-1]
            indicators['ema_200'] = ta.trend.EMAIndicator(close=data['Close'], window=min(200, len(data))).ema_indicator().iloc[-1]
            
            indicators['current_price'] = current_price
            
            return indicators
            
        except Exception as e:
            logger.error(f"Technical indicators failed for {symbol}: {e}")
            return {}

    def generate_technical_analysis(self, symbol: str) -> str:
        """Generate technical analysis report"""
        try:
            indicators = self.calculate_technical_indicators(symbol)
            if not indicators:
                return "Unable to perform technical analysis - insufficient data."

            current_price = indicators.get('current_price', 0)
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            bb_position = indicators.get('bb_position', 0.5)
            ema_50 = indicators.get('ema_50', 0)
            ema_200 = indicators.get('ema_200', 0)

            signals = []
            
            # RSI
            if rsi < 30:
                signals.append("RSI: OVERSOLD (Buy)")
            elif rsi > 70:
                signals.append("RSI: OVERBOUGHT (Sell)")
            else:
                signals.append(f"RSI: NEUTRAL ({rsi:.1f})")

            # MACD
            if macd > macd_signal:
                signals.append("MACD: BULLISH")
            else:
                signals.append("MACD: BEARISH")

            # Bollinger Bands
            if bb_position > 0.8:
                signals.append("Bollinger: UPPER BAND (Sell)")
            elif bb_position < 0.2:
                signals.append("Bollinger: LOWER BAND (Buy)")
            else:
                signals.append("Bollinger: MIDDLE RANGE")

            # EMA
            if ema_50 > ema_200:
                signals.append("EMA: GOLDEN CROSS (Buy)")
            else:
                signals.append("EMA: DEATH CROSS (Sell)")

            # Build report
            analysis = f"📊 **{symbol} Analysis**\n"
            analysis += f"💰 Price: ₹{current_price:.2f}\n\n"
            analysis += "\n".join(f"• {signal}" for signal in signals)
            
            # Overall recommendation
            buy_count = sum(1 for s in signals if 'buy' in s.lower() or 'bullish' in s.lower())
            sell_count = sum(1 for s in signals if 'sell' in s.lower() or 'bearish' in s.lower())
            
            if buy_count > sell_count:
                analysis += f"\n\n🟢 **BUY** ({buy_count} vs {sell_count})"
            elif sell_count > buy_count:
                analysis += f"\n\n🔴 **SELL** ({sell_count} vs {buy_count})"
            else:
                analysis += f"\n\n🟡 **HOLD** (Mixed signals)"

            return analysis
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return f"Error analyzing {symbol}"

    def get_stock_news(self, symbol: str, limit: int = 5) -> List[Dict]:
        """Get stock news"""
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            news = ticker.news or []
            
            processed_news = []
            for item in news[:limit]:
                processed_news.append({
                    'title': item.get('title', ''),
                    'publisher': item.get('publisher', ''),
                    'published': datetime.fromtimestamp(item.get('providerPublishTime', 0)),
                })
            
            return processed_news
            
        except Exception as e:
            logger.error(f"News failed for {symbol}: {e}")
            return []

    def validate_symbol(self, symbol: str) -> bool:
        """Check if stock symbol exists"""
        price = self.get_stock_price(symbol)
        return price is not None

    def is_market_open(self) -> bool:
        """Check if Indian market is open"""
        now = datetime.now()
        if now.weekday() >= 5:  # Weekend
            return False
        # Indian market: 9:15 AM - 3:30 PM
        return 9 <= now.hour <= 15