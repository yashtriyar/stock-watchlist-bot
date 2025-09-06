import google.generativeai as genai
from typing import List, Dict, Optional
import logging
from datetime import datetime
import config
from stocks import StockAnalyzer

logger = logging.getLogger(__name__)

class AIInsightsManager:
    def __init__(self):
        self.stock_analyzer = StockAnalyzer()
        self.setup_gemini()

    def setup_gemini(self):
        """Configure Gemini AI with updated model name"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            # Use the new model name - gemini-pro is deprecated
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Successfully configured Gemini AI with gemini-1.5-flash")
        except Exception as e:
            logger.error(f"Failed to setup Gemini AI: {e}")
            # Try fallback model names
            try:
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                logger.info("Using fallback model: gemini-1.5-pro")
            except:
                try:
                    self.model = genai.GenerativeModel('gemini-pro')
                    logger.info("Using legacy model: gemini-pro")
                except:
                    logger.error("All Gemini models failed")
                    self.model = None

    def generate_stock_insight(self, symbol: str) -> str:
        """Generate AI-powered stock insight"""
        if not self.model:
            return "AI insights unavailable - Gemini not configured"

        try:
            # Get technical indicators
            indicators = self.stock_analyzer.calculate_technical_indicators(symbol)
            if not indicators:
                return f"Unable to generate insights for {symbol} - insufficient data"

            # Get latest news
            news = self.stock_analyzer.get_stock_news(symbol, limit=3)
            
            # Format technical indicators summary
            tech_summary = self._format_technical_summary(indicators)
            
            # Format news summary
            news_summary = self._format_news_summary(news)
            
            # Create prompt for Gemini
            prompt = f"""You are a professional stock market assistant with expertise in technical analysis and market sentiment.

Analyze the stock: {symbol.upper()}

Technical Indicators Summary:
{tech_summary}

Recent News Headlines:
{news_summary}

Provide a concise actionable insight (maximum 4 lines):
- Clear Buy/Sell/Hold recommendation with confidence level
- Primary reason combining technical patterns and market sentiment  
- Short-term outlook (next 1-2 weeks)
- One key risk or opportunity to watch

Keep it professional, actionable, and under 200 words."""

            # Generate insight
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                insight = response.text.strip()
                logger.info(f"Generated AI insight for {symbol}")
                return f"🤖 AI Insight for {symbol}:\n\n{insight}"
            else:
                return f"Unable to generate AI insight for {symbol}"
                
        except Exception as e:
            logger.error(f"Failed to generate AI insight for {symbol}: {e}")
            return f"Error generating AI insight for {symbol}: {str(e)}"

    def analyze_portfolio(self, stocks_data: List[Dict]) -> str:
        """Generate portfolio-level insights"""
        if not self.model or not stocks_data:
            return "Portfolio analysis unavailable"

        try:
            portfolio_summary = []
            total_value = 0
            winners = 0
            losers = 0
            
            for stock in stocks_data:
                symbol = stock.get('Stock Symbol', '')
                buy_price = float(stock.get('Buy Price', 0))
                current_price = float(stock.get('Current Price', 0))
                
                if buy_price > 0 and current_price > 0:
                    pnl_percent = ((current_price - buy_price) / buy_price) * 100
                    portfolio_summary.append(f"{symbol}: {pnl_percent:+.1f}%")
                    
                    if pnl_percent > 0:
                        winners += 1
                    else:
                        losers += 1

            prompt = f"""You are a portfolio manager analyzing a stock watchlist.

Portfolio Performance:
{chr(10).join(portfolio_summary)}

Winners: {winners} stocks
Losers: {losers} stocks

Provide a brief portfolio analysis (maximum 5 lines):
- Overall portfolio health assessment
- Sector diversification comment if patterns visible
- Risk management observation
- One actionable recommendation for the portfolio

Keep it concise and actionable."""

            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return f"📊 Portfolio Analysis:\n\n{response.text.strip()}"
            else:
                return "Unable to generate portfolio analysis"
                
        except Exception as e:
            logger.error(f"Failed to analyze portfolio: {e}")
            return f"Error analyzing portfolio: {str(e)}"

    def get_buy_sell_advice(self, symbol: str, action_type: str) -> str:
        """Get specific buy or sell advice"""
        if not self.model:
            return f"{action_type.title()} advice unavailable - AI not configured"

        try:
            # Get current technical analysis
            indicators = self.stock_analyzer.calculate_technical_indicators(symbol)
            news = self.stock_analyzer.get_stock_news(symbol, limit=2)
            
            tech_summary = self._format_technical_summary(indicators)
            news_summary = self._format_news_summary(news)
            
            prompt = f"""You are a trading advisor. A trader wants specific {action_type.upper()} advice for {symbol.upper()}.

Current Technical Status:
{tech_summary}

Recent Market News:
{news_summary}

Provide focused {action_type} advice (maximum 3 lines):
- Should they {action_type} now? (Yes/No with confidence %)
- Best {action_type} strategy (timing, price levels)
- Key factor supporting your {action_type} recommendation

Be direct and actionable."""

            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return f"💡 {action_type.title()} Advice for {symbol}:\n\n{response.text.strip()}"
            else:
                return f"Unable to generate {action_type} advice for {symbol}"
                
        except Exception as e:
            logger.error(f"Failed to generate {action_type} advice for {symbol}: {e}")
            return f"Error generating {action_type} advice: {str(e)}"

    def _format_technical_summary(self, indicators: Dict) -> str:
        """Format technical indicators for AI prompt"""
        if not indicators:
            return "Technical data unavailable"
        
        summary = []
        
        # RSI
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            summary.append(f"RSI: {rsi:.1f} (Oversold)")
        elif rsi > 70:
            summary.append(f"RSI: {rsi:.1f} (Overbought)")
        else:
            summary.append(f"RSI: {rsi:.1f} (Neutral)")
        
        # MACD
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        if macd > macd_signal:
            summary.append("MACD: Bullish crossover")
        else:
            summary.append("MACD: Bearish crossover")
        
        # Bollinger Bands
        bb_position = indicators.get('bb_position', 0.5)
        if bb_position > 0.8:
            summary.append("Bollinger Bands: Near upper band")
        elif bb_position < 0.2:
            summary.append("Bollinger Bands: Near lower band")
        else:
            summary.append("Bollinger Bands: Middle range")
        
        # EMA Crossover
        ema_50 = indicators.get('ema_50', 0)
        ema_200 = indicators.get('ema_200', 0)
        if ema_50 > ema_200:
            summary.append("EMA: Golden cross (50 > 200)")
        else:
            summary.append("EMA: Death cross (50 < 200)")
        
        return " | ".join(summary)

    def _format_news_summary(self, news: List[Dict]) -> str:
        """Format news for AI prompt"""
        if not news:
            return "No recent news available"
        
        headlines = []
        for item in news:
            title = item.get('title', '')
            if title:
                headlines.append(f"• {title[:80]}...")
        
        return "\n".join(headlines) if headlines else "No recent news available"

    def get_market_sentiment(self, symbol: str) -> str:
        """Analyze market sentiment for a stock"""
        if not self.model:
            return "Sentiment analysis unavailable"

        try:
            news = self.stock_analyzer.get_stock_news(symbol, limit=5)
            if not news:
                return f"No recent news found for sentiment analysis of {symbol}"

            news_text = "\n".join([item.get('title', '') + " " + item.get('summary', '')[:100] 
                                 for item in news])

            prompt = f"""Analyze the market sentiment for {symbol.upper()} based on recent news:

{news_text}

Provide sentiment analysis:
- Overall sentiment: Positive/Negative/Neutral (with confidence %)
- Key sentiment drivers (1-2 factors)
- Sentiment trend: Improving/Declining/Stable

Keep response under 100 words."""

            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return f"📰 Market Sentiment for {symbol}:\n\n{response.text.strip()}"
            else:
                return f"Unable to analyze sentiment for {symbol}"
                
        except Exception as e:
            logger.error(f"Failed to analyze sentiment for {symbol}: {e}")
            return f"Error analyzing sentiment: {str(e)}"