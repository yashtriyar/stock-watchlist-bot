import asyncio
import logging
import sys
import signal
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import config
from telegram_bot import TelegramBot
from sheets import GoogleSheetsManager
from stocks import StockAnalyzer
from ai_insights import AIInsightsManager
from alerts import AlertManager
import threading

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('stock_bot.log', encoding='utf-8')
    ]
)

# Fix console encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logger = logging.getLogger(__name__)

class StockWatchlistBot:
    def __init__(self):
        self.telegram_bot = TelegramBot()
        self.sheets_manager = GoogleSheetsManager()
        self.stock_analyzer = StockAnalyzer()
        self.ai_insights = AIInsightsManager()
        self.alert_manager = AlertManager()
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def monitor_stocks(self):
        """Main monitoring function that runs every 5 minutes"""
        try:
            logger.info("Starting stock monitoring cycle...")
            
            # Get all stocks from watchlist
            stocks = self.sheets_manager.get_all_stocks()
            if not stocks:
                logger.info("No stocks in watchlist")
                return
            
            logger.info(f"Monitoring {len(stocks)} stocks")
            
            # Get current prices for all stocks
            symbols = [stock.get('Stock Symbol', '') for stock in stocks]
            current_prices = self.stock_analyzer.bulk_get_prices(symbols)
            
            # Update prices in Google Sheets
            if current_prices:
                self.sheets_manager.bulk_update_prices(current_prices)
                logger.info(f"Updated prices for {len(current_prices)} stocks")
            
            # Check for alerts
            all_alerts = []
            
            for stock in stocks:
                symbol = stock.get('Stock Symbol', '')
                
                # Update stock data with current price
                if symbol in current_prices:
                    stock['Current Price'] = current_prices[symbol]
                
                # Check price alerts (target/stop loss)
                price_alerts = self.alert_manager.check_price_alerts(stock)
                all_alerts.extend(price_alerts)
                
                # Check technical alerts
                indicators = self.stock_analyzer.calculate_technical_indicators(symbol)
                if indicators:
                    tech_alerts = self.alert_manager.check_technical_alerts(symbol, indicators)
                    all_alerts.extend(tech_alerts)
            
            # Check portfolio-level alerts
            portfolio_alerts = self.alert_manager.check_portfolio_alerts(stocks)
            all_alerts.extend(portfolio_alerts)
            
            # Filter duplicate alerts
            filtered_alerts = self.alert_manager.filter_duplicate_alerts(all_alerts)
            
            # Send alerts if any
            if filtered_alerts:
                logger.info(f"Sending {len(filtered_alerts)} alerts")
                await self.telegram_bot.send_bulk_alerts(filtered_alerts)
            else:
                logger.info("No new alerts to send")
            
            # Log market status
            market_open = self.stock_analyzer.is_market_open()
            logger.info(f"Market status: {'Open' if market_open else 'Closed'}")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            # Send error notification if critical
            if config.CHAT_ID:
                error_message = f"🚨 **Monitoring Error**\n\n{str(e)}\n\nBot will continue monitoring..."
                try:
                    await self.telegram_bot.send_alert(config.CHAT_ID, error_message)
                except:
                    pass
    # Add this to your existing main.py StockWatchlistBot class

    async def send_keepalive_ping(self):
        """Send keepalive ping to prevent Render from sleeping"""
        try:
            if config.CHAT_ID:
                # Send silent status message
                message = f"🔄 System active - {datetime.now().strftime('%H:%M')}"
                
                # Make it less intrusive - send only during market hours
                now = datetime.now()
                if 9 <= now.hour <= 16:  # Only during market hours
                    await self.telegram_bot.send_alert(config.CHAT_ID, message)
                    logger.info("Sent keepalive ping")
                else:
                    logger.info("Skipped keepalive ping (after market hours)")
                    
        except Exception as e:
            logger.error(f"Failed to send keepalive ping: {e}")

    def setup_scheduler(self):
        """Setup the job scheduler with keepalive"""
        try:
            # Stock monitoring every 5 minutes
            self.scheduler.add_job(
                self.monitor_stocks,
                IntervalTrigger(minutes=config.UPDATE_INTERVAL_MINUTES),
                id='monitor_stocks',
                name='Monitor Stock Prices and Alerts',
                replace_existing=True
            )
            
            # Keepalive ping every 14 minutes
            self.scheduler.add_job(
                self.send_keepalive_ping,
                IntervalTrigger(minutes=14),
                id='keepalive_ping',
                name='Keepalive Ping',
                replace_existing=True
            )
            
            # Daily summary at 9 AM EST
            self.scheduler.add_job(
                self.daily_summary,
                'cron',
                hour=9,
                minute=0,
                id='daily_summary',
                name='Daily Portfolio Summary',
                replace_existing=True
            )
            
            logger.info("Scheduler setup completed with keepalive")
            
        except Exception as e:
            logger.error(f"Failed to setup scheduler: {e}")
            raise

    async def daily_summary(self):
        """Send daily portfolio summary"""
        try:
            logger.info("Generating daily summary...")
            
            stocks = self.sheets_manager.get_all_stocks()
            if not stocks:
                return
            
            # Calculate daily performance
            total_positions = len(stocks)
            profitable = sum(1 for stock in stocks if self.telegram_bot._calculate_pnl(stock) > 0)
            
            summary_message = f"📊 **Daily Summary - {datetime.now().strftime('%m/%d/%Y')}**\n\n"
            summary_message += f"📈 **Portfolio Status:**\n"
            summary_message += f"• Total Positions: {total_positions}\n"
            summary_message += f"• Profitable: {profitable}/{total_positions}\n"
            summary_message += f"• Win Rate: {(profitable/total_positions)*100:.1f}%\n\n"
            
            # Top performers
            stocks_with_pnl = [(stock, self.telegram_bot._calculate_pnl(stock)) for stock in stocks]
            stocks_with_pnl.sort(key=lambda x: x[1], reverse=True)
            
            if stocks_with_pnl:
                best_stock, best_pnl = stocks_with_pnl[0]
                worst_stock, worst_pnl = stocks_with_pnl[-1]
                
                summary_message += f"🏆 **Best Performer:** {best_stock.get('Stock Symbol', '')} ({best_pnl:+.1f}%)\n"
                summary_message += f"📉 **Worst Performer:** {worst_stock.get('Stock Symbol', '')} ({worst_pnl:+.1f}%)\n\n"
            
            summary_message += f"🤖 **AI Insights:** Use `/portfolio` for detailed analysis\n"
            summary_message += f"📱 **Commands:** `/list` to view all positions"
            
            if config.CHAT_ID:
                await self.telegram_bot.send_alert(config.CHAT_ID, summary_message)
                
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")

    def setup_scheduler(self):
        """Setup the job scheduler"""
        try:
            # Stock monitoring every 5 minutes
            self.scheduler.add_job(
                self.monitor_stocks,
                IntervalTrigger(minutes=config.UPDATE_INTERVAL_MINUTES),
                id='monitor_stocks',
                name='Monitor Stock Prices and Alerts',
                replace_existing=True
            )
            
            # Daily summary at 9 AM EST
            self.scheduler.add_job(
                self.daily_summary,
                'cron',
                hour=9,
                minute=0,
                id='daily_summary',
                name='Daily Portfolio Summary',
                replace_existing=True
            )
            
            logger.info("Scheduler setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup scheduler: {e}")
            raise

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown()

    def shutdown(self):
        """Shutdown the application gracefully"""
        try:
            self.is_running = False
            if self.scheduler.running:
                self.scheduler.shutdown()
            logger.info("Application shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def startup_check(self):
        """Perform startup checks and send notification"""
        try:
            logger.info("Performing startup checks...")
            
            # Test Google Sheets connection
            stocks = self.sheets_manager.get_all_stocks()
            logger.info(f"Google Sheets: Connected ({len(stocks)} stocks in watchlist)")
            
            # Test stock data API with better error handling
            try:
                test_price = self.stock_analyzer.get_stock_price('AAPL')
                if test_price:
                    logger.info(f"Yahoo Finance API: Connected (AAPL: ${test_price})")
                else:
                    logger.warning("Yahoo Finance API: Connected but no price data (may be market hours)")
            except Exception as e:
                logger.warning(f"Yahoo Finance API: Issues detected - {e}")
            
            # Test AI service
            if config.GEMINI_API_KEY:
                logger.info("Gemini AI: Configured")
            else:
                logger.warning("Gemini AI: Not configured")
            
            # Send startup notification
            if config.CHAT_ID:
                startup_message = f"🤖 **Stock Watchlist Bot Started!**\n\n"
                startup_message += f"📊 **Status:**\n"
                startup_message += f"• Monitoring {len(stocks)} stocks\n"
                startup_message += f"• Update interval: {config.UPDATE_INTERVAL_MINUTES} minutes\n"
                startup_message += f"• Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                startup_message += f"🔔 **Alerts enabled for:**\n"
                startup_message += f"• Price targets & stop losses\n"
                startup_message += f"• Technical analysis signals\n"
                startup_message += f"• Portfolio performance\n\n"
                startup_message += f"📱 Use `/help` for available commands"
                
                await self.telegram_bot.send_alert(config.CHAT_ID, startup_message)
            
            logger.info("Startup checks completed successfully")
            
        except Exception as e:
            logger.error(f"Startup check failed: {e}")
            if config.CHAT_ID:
                error_message = f"🚨 **Startup Error**\n\n{str(e)}\n\nSome features may not work properly."
                try:
                    await self.telegram_bot.send_alert(config.CHAT_ID, error_message)
                except:
                    pass

    async def run(self):
        """Main application runner"""
        try:
            logger.info("Starting Stock Watchlist Bot...")
            
            # Validate configuration
            if not all([config.TELEGRAM_BOT_TOKEN, config.GOOGLE_SHEET_ID, config.GOOGLE_SHEETS_CREDENTIALS]):
                raise ValueError("Missing required configuration: Check TELEGRAM_BOT_TOKEN, GOOGLE_SHEET_ID, GOOGLE_SHEETS_CREDENTIALS")
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Perform startup checks
            await self.startup_check()
            
            # Setup and start scheduler
            self.setup_scheduler()
            self.scheduler.start()
            logger.info("Scheduler started")
            
            self.is_running = True
            
            # Start Telegram bot - Use polling for local development
            logger.info("Starting Telegram bot...")
            
            # Always use polling for local development
            # Webhook is handled separately in production
            self.telegram_bot.start_polling()
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.shutdown()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.shutdown()
            sys.exit(1)

    async def _run_polling(self):
        """Run bot polling in async mode"""
        try:
            # Create a task for bot polling
            bot_task = asyncio.create_task(self._bot_polling())
            
            # Keep the main loop running
            while self.is_running:
                await asyncio.sleep(1)
                
            # Cancel bot task on shutdown
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
                
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            self.shutdown()

    async def _bot_polling(self):
        """Async wrapper for bot polling"""
        try:
            await self.telegram_bot.app.initialize()
            await self.telegram_bot.app.start()
            
            # Start polling
            await self.telegram_bot.app.updater.start_polling(drop_pending_updates=True)
            
            # Keep polling until shutdown
            while self.is_running:
                await asyncio.sleep(1)
                
            # Stop polling
            await self.telegram_bot.app.updater.stop()
            await self.telegram_bot.app.stop()
            await self.telegram_bot.app.shutdown()
            
        except Exception as e:
            logger.error(f"Error in bot polling: {e}")

def main():
    """Main entry point"""
    try:
        # Create and run the bot (no Flask needed)
        bot = StockWatchlistBot()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(bot.run())
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()
