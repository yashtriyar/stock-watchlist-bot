import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import re
from typing import List, Dict
import config
from sheets import GoogleSheetsManager
from stocks import StockAnalyzer
from ai_insights import AIInsightsManager
from alerts import AlertManager

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.app = None
        self.sheets_manager = GoogleSheetsManager()
        self.stock_analyzer = StockAnalyzer()
        self.ai_insights = AIInsightsManager()
        self.alert_manager = AlertManager()
        self.setup_bot()

    def setup_bot(self):
        """Initialize the Telegram bot"""
        try:
            self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
            
            # Command handlers
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("help", self.help_command))
            self.app.add_handler(CommandHandler("add_stock", self.add_stock_command))
            self.app.add_handler(CommandHandler("remove_stock", self.remove_stock_command))
            self.app.add_handler(CommandHandler("list", self.list_stocks_command))
            self.app.add_handler(CommandHandler("news", self.news_command))
            self.app.add_handler(CommandHandler("insights", self.insights_command))
            self.app.add_handler(CommandHandler("alerts", self.alerts_command))
            self.app.add_handler(CommandHandler("portfolio", self.portfolio_command))
            
            # Callback handlers for inline buttons
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))
            
            logger.info("Telegram bot setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup Telegram bot: {e}")
            raise

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 **Stock Watchlist AI Assistant**

Welcome! I help you track stocks and provide AI-powered insights.

**Available Commands:**
• `/add_stock SYMBOL buy=XX target=YY stop=ZZ notes=TEXT` - Add stock to watchlist
• `/remove_stock SYMBOL` - Remove stock from watchlist  
• `/list` - Show your watchlist with current prices
• `/news SYMBOL` - Get latest news for a stock
• `/insights SYMBOL` - Get AI analysis and recommendations
• `/alerts` - Show recent alerts
• `/portfolio` - Portfolio overview and analysis

**Example:**
`/add_stock AAPL buy=150 target=180 stop=140 notes=Tech giant`

Let's start building your watchlist! 📈
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
📚 **Help - Stock Watchlist Commands**

**Stock Management:**
• `/add_stock SYMBOL buy=XX target=YY stop=ZZ notes=TEXT`
  Example: `/add_stock TSLA buy=200 target=250 stop=180 notes=EV leader`

• `/remove_stock SYMBOL`
  Example: `/remove_stock TSLA`

• `/list` - View all stocks in watchlist

**Analysis & Insights:**
• `/news SYMBOL` - Latest news headlines
• `/insights SYMBOL` - AI-powered analysis  
• `/alerts` - Recent price and technical alerts
• `/portfolio` - Portfolio performance overview

**Interactive Features:**
When you use `/list`, you'll see buttons for each stock:
• 🔍 **Buy Advice** - AI recommendation for buying
• 💰 **Sell Advice** - AI recommendation for selling  
• 📰 **News** - Latest headlines
• 📊 **Chart Analysis** - Technical indicators

**Automated Features:**
• Price updates every 5 minutes
• Automatic alerts when targets/stop-losses hit
• Technical analysis alerts (RSI, MACD, etc.)
• AI insights combining news + technical data

Need help? Just ask! 🚀
        """
        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def add_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_stock command"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ **Usage:** `/add_stock SYMBOL buy=XX target=YY stop=ZZ notes=TEXT`\n\n"
                    "**Example:** `/add_stock AAPL buy=150 target=180 stop=140 notes=Tech stock`",
                    parse_mode='Markdown'
                )
                return

            # Parse command arguments
            args_text = ' '.join(context.args)
            
            # Extract symbol (first argument)
            symbol = context.args[0].upper()
            
            # Parse parameters using regex
            buy_match = re.search(r'buy=([0-9.]+)', args_text)
            target_match = re.search(r'target=([0-9.]+)', args_text)
            stop_match = re.search(r'stop=([0-9.]+)', args_text)
            notes_match = re.search(r'notes=(.+?)(?:\s+(?:buy|target|stop)=|$)', args_text)
            
            if not all([buy_match, target_match, stop_match]):
                await update.message.reply_text(
                    "❌ **Missing parameters!**\n\n"
                    "Required: `buy=XX target=YY stop=ZZ`\n"
                    "Example: `/add_stock AAPL buy=150 target=180 stop=140`",
                    parse_mode='Markdown'
                )
                return
            
            buy_price = float(buy_match.group(1))
            target_price = float(target_match.group(1))
            stop_loss = float(stop_match.group(1))
            notes = notes_match.group(1).strip() if notes_match else ""
            
            # Validate symbol
            if not self.stock_analyzer.validate_symbol(symbol):
                await update.message.reply_text(f"❌ **Invalid stock symbol:** {symbol}")
                return
            
            # Validate price logic
            if target_price <= buy_price:
                await update.message.reply_text("❌ **Target price must be higher than buy price**")
                return
            
            if stop_loss >= buy_price:
                await update.message.reply_text("❌ **Stop loss must be lower than buy price**")
                return
            
            # Add to Google Sheets
            success = self.sheets_manager.add_stock(symbol, buy_price, target_price, stop_loss, notes)
            
            if success:
                # Get current price
                current_price = self.stock_analyzer.get_stock_price(symbol)
                if current_price:
                    self.sheets_manager.update_current_price(symbol, current_price)
                
                await update.message.reply_text(
                    f"✅ **Added {symbol} to watchlist!**\n\n"
                    f"📊 **Details:**\n"
                    f"• Buy Price: ₹{buy_price:.2f}\n"
                    f"• Target: ₹{target_price:.2f}\n"
                    f"• Stop Loss: ₹{stop_loss:.2f}\n"
                    f"• Current Price: ₹{current_price:.2f}\n"
                    f"• Notes: {notes}\n\n"
                    f"🤖 I'll monitor this stock and send alerts!",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"❌ **Failed to add {symbol}** - Please try again")
                
        except ValueError:
            await update.message.reply_text("❌ **Invalid price format!** Use numbers only (e.g., 150.50)")
        except Exception as e:
            logger.error(f"Failed to add stock: {e}")
            await update.message.reply_text(f"❌ **Error adding stock:** {str(e)}")

    async def remove_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove_stock command"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ **Usage:** `/remove_stock SYMBOL`\n\n"
                    "**Example:** `/remove_stock AAPL`",
                    parse_mode='Markdown'
                )
                return
            
            symbol = context.args[0].upper()
            
            # Check if stock exists
            stock_data = self.sheets_manager.get_stock_by_symbol(symbol)
            if not stock_data:
                await update.message.reply_text(f"❌ **{symbol} not found** in your watchlist")
                return
            
            # Remove from sheets
            success = self.sheets_manager.remove_stock(symbol)
            
            if success:
                await update.message.reply_text(
                    f"✅ **Removed {symbol}** from watchlist\n\n"
                    f"📊 **Removed stock details:**\n"
                    f"• Buy Price: ₹{stock_data.get('Buy Price', 0)}\n"
                    f"• Current Price: ₹{stock_data.get('Current Price', 0)}\n"
                    f"• Final P&L: {self._calculate_pnl(stock_data):.1f}%",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"❌ **Failed to remove {symbol}** - Please try again")
                
        except Exception as e:
            logger.error(f"Failed to remove stock: {e}")
            await update.message.reply_text(f"❌ **Error:** {str(e)}")

    async def list_stocks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command with inline buttons"""
        try:
            stocks = self.sheets_manager.get_all_stocks()
            
            if not stocks:
                await update.message.reply_text(
                    "📋 **Your watchlist is empty**\n\n"
                    "Add stocks using: `/add_stock SYMBOL buy=XX target=YY stop=ZZ`",
                    parse_mode='Markdown'
                )
                return
            
            # Create message with stock list
            message = "📋 **Your Stock Watchlist**\n\n"
            
            for i, stock in enumerate(stocks, 1):
                symbol = stock.get('Stock Symbol', '')
                buy_price = float(stock.get('Buy Price', 0))
                current_price = float(stock.get('Current Price', 0))
                target_price = float(stock.get('Target Price', 0))
                stop_loss = float(stock.get('Stop Loss', 0))
                
                pnl = self._calculate_pnl(stock)
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                
                # Distance to target and stop loss
                target_distance = ((target_price - current_price) / current_price) * 100 if current_price > 0 else 0
                stop_distance = ((current_price - stop_loss) / current_price) * 100 if current_price > 0 else 0
                
                message += f"**{i}. {symbol}** {pnl_emoji}\n"
                message += f"💰 Current: ₹{current_price:.2f} | P&L: {pnl:+.1f}%\n"
                message += f"🎯 Target: ₹{target_price:.2f} ({target_distance:+.1f}%)\n"
                message += f"🛑 Stop: ₹{stop_loss:.2f} ({stop_distance:+.1f}%)\n\n"
            
            # Create inline keyboard for each stock
            keyboard = []
            for stock in stocks:
                symbol = stock.get('Stock Symbol', '')
                row = [
                    InlineKeyboardButton(f"🔍 {symbol} Buy", callback_data=f"buy_advice_{symbol}"),
                    InlineKeyboardButton(f"💰 {symbol} Sell", callback_data=f"sell_advice_{symbol}"),
                ]
                keyboard.append(row)
                
                row2 = [
                    InlineKeyboardButton(f"📰 {symbol} News", callback_data=f"news_{symbol}"),
                    InlineKeyboardButton(f"📊 {symbol} Chart", callback_data=f"chart_{symbol}"),
                ]
                keyboard.append(row2)
            
            # Add portfolio summary button
            keyboard.append([InlineKeyboardButton("📊 Portfolio Analysis", callback_data="portfolio_analysis")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Failed to list stocks: {e}")
            await update.message.reply_text(f"❌ **Error:** {str(e)}")

    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ **Usage:** `/news SYMBOL`\n\n"
                    "**Example:** `/news AAPL`",
                    parse_mode='Markdown'
                )
                return
            
            symbol = context.args[0].upper()
            
            # Get news
            news_items = self.stock_analyzer.get_stock_news(symbol, limit=5)
            
            if not news_items:
                await update.message.reply_text(f"📰 **No recent news found for {symbol}**")
                return
            
            message = f"📰 **Latest News for {symbol}**\n\n"
            
            for i, news in enumerate(news_items, 1):
                title = news.get('title', '')[:100]
                publisher = news.get('publisher', 'Unknown')
                published = news.get('published', '')
                
                message += f"**{i}. {title}**\n"
                message += f"📅 {published.strftime('%m/%d %H:%M') if hasattr(published, 'strftime') else 'Recent'} | {publisher}\n\n"
            
            # Add sentiment analysis button
            keyboard = [[InlineKeyboardButton(f"🤖 AI Sentiment Analysis", callback_data=f"sentiment_{symbol}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Failed to get news: {e}")
            await update.message.reply_text(f"❌ **Error:** {str(e)}")

    async def insights_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /insights command"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ **Usage:** `/insights SYMBOL`\n\n"
                    "**Example:** `/insights AAPL`",
                    parse_mode='Markdown'
                )
                return
            
            symbol = context.args[0].upper()
            
            # Show loading message
            loading_msg = await update.message.reply_text(f"🤖 **Analyzing {symbol}**...\nGenerating AI insights...")
            
            # Get AI insights
            ai_insight = self.ai_insights.generate_stock_insight(symbol)
            
            # Get technical analysis
            tech_analysis = self.stock_analyzer.generate_technical_analysis(symbol)
            
            # Combine insights
            full_message = f"{ai_insight}\n\n---\n\n{tech_analysis}"
            
            # Delete loading message and send results
            await loading_msg.delete()
            await update.message.reply_text(full_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get insights: {e}")
            await update.message.reply_text(f"❌ **Error:** {str(e)}")

    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command"""
        try:
            # Get recent alerts from alert manager history
            recent_alerts = self.alert_manager.alert_history[-10:]  # Last 10 alerts
            
            if not recent_alerts:
                await update.message.reply_text(
                    "📭 **No recent alerts**\n\n"
                    "I'll notify you when:\n"
                    "• Target prices are hit 🎯\n"
                    "• Stop losses are triggered 🛑\n"
                    "• Technical signals occur 📊\n"
                    "• Important news breaks 📰",
                    parse_mode='Markdown'
                )
                return
            
            message = "🔔 **Recent Alerts**\n\n"
            
            for alert in reversed(recent_alerts):  # Show newest first
                timestamp = alert['timestamp'].strftime("%m/%d %H:%M")
                symbol = alert.get('symbol', 'Unknown')
                alert_type = alert.get('type', '').replace('_', ' ').title()
                priority = alert.get('priority', 'LOW')
                
                priority_emoji = {'CRITICAL': '🚨', 'HIGH': '❗', 'MEDIUM': '⚠️', 'LOW': 'ℹ️'}
                emoji = priority_emoji.get(priority, 'ℹ️')
                
                message += f"{emoji} **{symbol}** - {alert_type}\n"
                message += f"📅 {timestamp}\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to show alerts: {e}")
            await update.message.reply_text(f"❌ **Error:** {str(e)}")

    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command"""
        try:
            stocks = self.sheets_manager.get_all_stocks()
            
            if not stocks:
                await update.message.reply_text("📋 **Portfolio is empty** - Add some stocks first!")
                return
            
            # Calculate portfolio metrics
            total_positions = len(stocks)
            profitable = 0
            total_pnl = 0
            best_performer = None
            worst_performer = None
            best_pnl = float('-inf')
            worst_pnl = float('inf')
            
            message = f"📊 **Portfolio Overview**\n"
            message += f"📈 **Total Positions:** {total_positions}\n\n"
            
            for stock in stocks:
                pnl = self._calculate_pnl(stock)
                total_pnl += pnl
                
                if pnl > 0:
                    profitable += 1
                
                if pnl > best_pnl:
                    best_pnl = pnl
                    best_performer = stock.get('Stock Symbol', '')
                
                if pnl < worst_pnl:
                    worst_pnl = pnl
                    worst_performer = stock.get('Stock Symbol', '')
            
            avg_pnl = total_pnl / total_positions if total_positions > 0 else 0
            win_rate = (profitable / total_positions) * 100 if total_positions > 0 else 0
            
            # Performance metrics
            message += f"📊 **Performance:**\n"
            message += f"• Average P&L: {avg_pnl:+.1f}%\n"
            message += f"• Win Rate: {win_rate:.1f}% ({profitable}/{total_positions})\n"
            message += f"• Best: {best_performer} ({best_pnl:+.1f}%)\n"
            message += f"• Worst: {worst_performer} ({worst_pnl:+.1f}%)\n\n"
            
            # Risk analysis
            message += f"⚖️ **Risk Analysis:**\n"
            if avg_pnl < -5:
                message += f"🔴 High portfolio risk - Average loss {avg_pnl:.1f}%\n"
            elif avg_pnl > 5:
                message += f"🟢 Strong performance - Average gain {avg_pnl:.1f}%\n"
            else:
                message += f"🟡 Neutral performance - Average {avg_pnl:+.1f}%\n"
            
            if win_rate < 40:
                message += f"⚠️ Low win rate - Review strategy\n"
            elif win_rate > 60:
                message += f"✅ Good win rate - Strategy working\n"
            
            # Add AI analysis button
            keyboard = [[InlineKeyboardButton("🤖 AI Portfolio Analysis", callback_data="portfolio_ai_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Failed to show portfolio: {e}")
            await update.message.reply_text(f"❌ **Error:** {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            callback_data = query.data
            
            if callback_data.startswith("buy_advice_"):
                symbol = callback_data.replace("buy_advice_", "")
                advice = self.ai_insights.get_buy_sell_advice(symbol, "buy")
                await query.edit_message_text(advice, parse_mode='Markdown')
                
            elif callback_data.startswith("sell_advice_"):
                symbol = callback_data.replace("sell_advice_", "")
                advice = self.ai_insights.get_buy_sell_advice(symbol, "sell")
                await query.edit_message_text(advice, parse_mode='Markdown')
                
            elif callback_data.startswith("news_"):
                symbol = callback_data.replace("news_", "")
                news_items = self.stock_analyzer.get_stock_news(symbol, limit=3)
                
                if news_items:
                    message = f"📰 **Latest News for {symbol}**\n\n"
                    for i, news in enumerate(news_items, 1):
                        title = news.get('title', '')[:80]
                        publisher = news.get('publisher', 'Unknown')
                        message += f"**{i}. {title}**\n📅 {publisher}\n\n"
                else:
                    message = f"📰 **No recent news for {symbol}**"
                
                await query.edit_message_text(message, parse_mode='Markdown')
                
            elif callback_data.startswith("chart_"):
                symbol = callback_data.replace("chart_", "")
                analysis = self.stock_analyzer.generate_technical_analysis(symbol)
                await query.edit_message_text(analysis, parse_mode='Markdown')
                
            elif callback_data.startswith("sentiment_"):
                symbol = callback_data.replace("sentiment_", "")
                sentiment = self.ai_insights.get_market_sentiment(symbol)
                await query.edit_message_text(sentiment, parse_mode='Markdown')
                
            elif callback_data == "portfolio_analysis":
                stocks = self.sheets_manager.get_all_stocks()
                analysis = self.ai_insights.analyze_portfolio(stocks)
                await query.edit_message_text(analysis, parse_mode='Markdown')
                
            elif callback_data == "portfolio_ai_analysis":
                stocks = self.sheets_manager.get_all_stocks()
                analysis = self.ai_insights.analyze_portfolio(stocks)
                await query.edit_message_text(analysis, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Failed to handle callback: {e}")
            await query.edit_message_text(f"❌ **Error:** {str(e)}")

    def _calculate_pnl(self, stock_data: Dict) -> float:
        """Calculate P&L percentage for a stock"""
        try:
            buy_price = float(stock_data.get('Buy Price', 0))
            current_price = float(stock_data.get('Current Price', 0))
            
            if buy_price > 0 and current_price > 0:
                return ((current_price - buy_price) / buy_price) * 100
            return 0
        except:
            return 0

    async def send_alert(self, chat_id: str, message: str):
        """Send alert message to Telegram"""
        try:
            await self.app.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            logger.info(f"Alert sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    async def send_bulk_alerts(self, alerts: List[Dict]):
        """Send multiple alerts efficiently"""
        if not alerts or not config.CHAT_ID:
            return
        
        try:
            # Group alerts by priority
            critical_alerts = [a for a in alerts if a.get('priority') == 'CRITICAL']
            high_alerts = [a for a in alerts if a.get('priority') == 'HIGH']
            other_alerts = [a for a in alerts if a.get('priority') not in ['CRITICAL', 'HIGH']]
            
            # Send critical alerts immediately
            for alert in critical_alerts:
                message = self.alert_manager.format_alert_message(alert)
                await self.send_alert(config.CHAT_ID, message)
                await asyncio.sleep(1)  # Rate limiting
            
            # Send high priority alerts
            for alert in high_alerts:
                message = self.alert_manager.format_alert_message(alert)
                await self.send_alert(config.CHAT_ID, message)
                await asyncio.sleep(1)
            
            # Send summary for other alerts if any
            if other_alerts:
                summary = self.alert_manager.get_alert_summary(other_alerts)
                await self.send_alert(config.CHAT_ID, summary)
                
        except Exception as e:
            logger.error(f"Failed to send bulk alerts: {e}")

    def start_polling(self):
        """Start the bot polling - simplified version"""
        try:
            logger.info("Starting Telegram bot polling...")
            
            # Simple polling without event loop complications
            self.app.run_polling(
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"Failed to start bot polling: {e}")
            raise

    async def start_webhook(self, webhook_url: str, port: int = 8080):
        """Start webhook for production deployment"""
        try:
            await self.app.bot.set_webhook(url=webhook_url)
            self.app.run_webhook(
                listen="0.0.0.0",
                port=port,
                webhook_url=webhook_url
            )
            logger.info(f"Webhook started at {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to start webhook: {e}")
            raise