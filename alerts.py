import logging
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class AlertType(Enum):
    TARGET_HIT = "target_hit"
    STOP_LOSS = "stop_loss"
    TECHNICAL_BUY = "technical_buy"
    TECHNICAL_SELL = "technical_sell"
    NEWS_ALERT = "news_alert"
    VOLUME_SPIKE = "volume_spike"

class AlertManager:
    def __init__(self):
        self.alert_history = []
        self.cooldown_period = timedelta(hours=1)  # Prevent spam alerts

    def check_price_alerts(self, stock_data: Dict) -> List[Dict]:
        """Check for price-based alerts (target/stop-loss)"""
        alerts = []
        
        try:
            symbol = stock_data.get('Stock Symbol', '')
            current_price = float(stock_data.get('Current Price', 0))
            target_price = float(stock_data.get('Target Price', 0))
            stop_loss = float(stock_data.get('Stop Loss', 0))
            buy_price = float(stock_data.get('Buy Price', 0))
            
            if not all([current_price, target_price, stop_loss, buy_price]):
                return alerts

            # Check target price hit
            if current_price >= target_price:
                profit_percent = ((current_price - buy_price) / buy_price) * 100
                alert = {
                    'type': AlertType.TARGET_HIT,
                    'symbol': symbol,
                    'message': f"🎯 TARGET HIT: {symbol} reached ${current_price:.2f} (Target: ${target_price:.2f})\n"
                              f"💰 Profit: +{profit_percent:.1f}%\n"
                              f"💡 Consider taking profits or adjusting stop-loss",
                    'current_price': current_price,
                    'trigger_price': target_price,
                    'timestamp': datetime.now(),
                    'priority': 'HIGH'
                }
                alerts.append(alert)

            # Check stop loss hit
            elif current_price <= stop_loss:
                loss_percent = ((current_price - buy_price) / buy_price) * 100
                alert = {
                    'type': AlertType.STOP_LOSS,
                    'symbol': symbol,
                    'message': f"🛑 STOP LOSS HIT: {symbol} dropped to ${current_price:.2f} (Stop: ${stop_loss:.2f})\n"
                              f"📉 Loss: {loss_percent:.1f}%\n"
                              f"⚠️ Consider exiting position to limit losses",
                    'current_price': current_price,
                    'trigger_price': stop_loss,
                    'timestamp': datetime.now(),
                    'priority': 'CRITICAL'
                }
                alerts.append(alert)

            # Check for price approaching levels (5% buffer)
            target_buffer = target_price * 0.95
            stop_buffer = stop_loss * 1.05
            
            if target_buffer <= current_price < target_price:
                alert = {
                    'type': AlertType.TARGET_HIT,
                    'symbol': symbol,
                    'message': f"📈 APPROACHING TARGET: {symbol} at ${current_price:.2f}\n"
                              f"🎯 Target: ${target_price:.2f} (95% reached)\n"
                              f"💡 Monitor closely for exit opportunity",
                    'current_price': current_price,
                    'trigger_price': target_buffer,
                    'timestamp': datetime.now(),
                    'priority': 'MEDIUM'
                }
                alerts.append(alert)

            elif stop_loss < current_price <= stop_buffer:
                alert = {
                    'type': AlertType.STOP_LOSS,
                    'symbol': symbol,
                    'message': f"⚠️ APPROACHING STOP LOSS: {symbol} at ${current_price:.2f}\n"
                              f"🛑 Stop Loss: ${stop_loss:.2f}\n"
                              f"📊 Consider technical analysis for trend reversal",
                    'current_price': current_price,
                    'trigger_price': stop_buffer,
                    'timestamp': datetime.now(),
                    'priority': 'MEDIUM'
                }
                alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check price alerts for {stock_data.get('Stock Symbol', 'Unknown')}: {e}")

        return alerts

    def check_technical_alerts(self, symbol: str, indicators: Dict) -> List[Dict]:
        """Check for technical indicator alerts"""
        alerts = []
        
        try:
            if not indicators:
                return alerts

            # RSI alerts
            rsi = indicators.get('rsi', 50)
            if rsi <= 25:  # Severely oversold
                alert = {
                    'type': AlertType.TECHNICAL_BUY,
                    'symbol': symbol,
                    'message': f"📊 TECHNICAL BUY SIGNAL: {symbol}\n"
                              f"🔴 RSI: {rsi:.1f} (Severely Oversold)\n"
                              f"💡 Potential bounce opportunity",
                    'indicator': 'RSI',
                    'value': rsi,
                    'timestamp': datetime.now(),
                    'priority': 'HIGH'
                }
                alerts.append(alert)
            elif rsi >= 75:  # Severely overbought
                alert = {
                    'type': AlertType.TECHNICAL_SELL,
                    'symbol': symbol,
                    'message': f"📊 TECHNICAL SELL SIGNAL: {symbol}\n"
                              f"🔴 RSI: {rsi:.1f} (Severely Overbought)\n"
                              f"⚠️ Correction may be imminent",
                    'indicator': 'RSI',
                    'value': rsi,
                    'timestamp': datetime.now(),
                    'priority': 'HIGH'
                }
                alerts.append(alert)

            # MACD crossover alerts
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            macd_hist = indicators.get('macd_histogram', 0)
            
            # Bullish crossover (MACD crosses above signal line)
            if macd > macd_signal and abs(macd - macd_signal) < 0.1:  # Close crossover
                alert = {
                    'type': AlertType.TECHNICAL_BUY,
                    'symbol': symbol,
                    'message': f"📊 MACD BULLISH CROSSOVER: {symbol}\n"
                              f"📈 MACD crossed above signal line\n"
                              f"💡 Potential uptrend beginning",
                    'indicator': 'MACD',
                    'value': macd - macd_signal,
                    'timestamp': datetime.now(),
                    'priority': 'MEDIUM'
                }
                alerts.append(alert)

            # Bollinger Bands alerts
            bb_position = indicators.get('bb_position', 0.5)
            if bb_position <= 0.05:  # At lower band
                alert = {
                    'type': AlertType.TECHNICAL_BUY,
                    'symbol': symbol,
                    'message': f"📊 BOLLINGER BAND SQUEEZE: {symbol}\n"
                              f"📉 Price at lower Bollinger Band\n"
                              f"💡 Potential reversal opportunity",
                    'indicator': 'Bollinger Bands',
                    'value': bb_position,
                    'timestamp': datetime.now(),
                    'priority': 'MEDIUM'
                }
                alerts.append(alert)
            elif bb_position >= 0.95:  # At upper band
                alert = {
                    'type': AlertType.TECHNICAL_SELL,
                    'symbol': symbol,
                    'message': f"📊 BOLLINGER BAND EXTENSION: {symbol}\n"
                              f"📈 Price at upper Bollinger Band\n"
                              f"⚠️ Potential pullback ahead",
                    'indicator': 'Bollinger Bands',
                    'value': bb_position,
                    'timestamp': datetime.now(),
                    'priority': 'MEDIUM'
                }
                alerts.append(alert)

            # Golden Cross / Death Cross alerts
            ema_50 = indicators.get('ema_50', 0)
            ema_200 = indicators.get('ema_200', 0)
            current_price = indicators.get('current_price', 0)
            
            if ema_50 > ema_200 and abs(ema_50 - ema_200) / ema_200 < 0.02:  # Recent golden cross
                alert = {
                    'type': AlertType.TECHNICAL_BUY,
                    'symbol': symbol,
                    'message': f"📊 GOLDEN CROSS DETECTED: {symbol}\n"
                              f"🌟 50 EMA crossed above 200 EMA\n"
                              f"📈 Long-term bullish signal",
                    'indicator': 'EMA Cross',
                    'value': (ema_50 - ema_200) / ema_200,
                    'timestamp': datetime.now(),
                    'priority': 'HIGH'
                }
                alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check technical alerts for {symbol}: {e}")

        return alerts

    def filter_duplicate_alerts(self, new_alerts: List[Dict]) -> List[Dict]:
        """Filter out duplicate alerts based on cooldown period"""
        filtered_alerts = []
        current_time = datetime.now()
        
        for alert in new_alerts:
            # Check if similar alert was sent recently
            is_duplicate = False
            for historical_alert in self.alert_history:
                if (historical_alert['symbol'] == alert['symbol'] and
                    historical_alert['type'] == alert['type'] and
                    current_time - historical_alert['timestamp'] < self.cooldown_period):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_alerts.append(alert)
                # Add to history
                self.alert_history.append(alert)
        
        # Clean old alerts from history (keep last 100)
        self.alert_history = self.alert_history[-100:]
        
        return filtered_alerts

    def format_alert_message(self, alert: Dict) -> str:
        """Format alert message for Telegram"""
        priority_emoji = {
            'CRITICAL': '🚨',
            'HIGH': '❗',
            'MEDIUM': '⚠️',
            'LOW': 'ℹ️'
        }
        
        emoji = priority_emoji.get(alert.get('priority', 'LOW'), 'ℹ️')
        timestamp = alert['timestamp'].strftime("%H:%M:%S")
        
        return f"{emoji} **ALERT** - {timestamp}\n\n{alert['message']}"

    def get_alert_summary(self, alerts: List[Dict]) -> str:
        """Generate summary of multiple alerts"""
        if not alerts:
            return "No alerts at this time."
        
        summary = f"📋 **Alert Summary** ({len(alerts)} alerts)\n\n"
        
        # Group by priority
        critical = [a for a in alerts if a.get('priority') == 'CRITICAL']
        high = [a for a in alerts if a.get('priority') == 'HIGH']
        medium = [a for a in alerts if a.get('priority') == 'MEDIUM']
        
        if critical:
            summary += f"🚨 **CRITICAL ({len(critical)}):**\n"
            for alert in critical:
                summary += f"• {alert['symbol']}: {alert['type'].value.replace('_', ' ').title()}\n"
            summary += "\n"
        
        if high:
            summary += f"❗ **HIGH ({len(high)}):**\n"
            for alert in high:
                summary += f"• {alert['symbol']}: {alert['type'].value.replace('_', ' ').title()}\n"
            summary += "\n"
        
        if medium:
            summary += f"⚠️ **MEDIUM ({len(medium)}):**\n"
            for alert in medium:
                summary += f"• {alert['symbol']}: {alert['type'].value.replace('_', ' ').title()}\n"
        
        return summary

    def check_portfolio_alerts(self, stocks_data: List[Dict]) -> List[Dict]:
        """Check for portfolio-wide alerts"""
        alerts = []
        
        try:
            if not stocks_data:
                return alerts
            
            total_positions = len(stocks_data)
            profitable_positions = 0
            losing_positions = 0
            total_pnl = 0
            
            for stock in stocks_data:
                try:
                    buy_price = float(stock.get('Buy Price', 0))
                    current_price = float(stock.get('Current Price', 0))
                    
                    if buy_price > 0 and current_price > 0:
                        pnl_percent = ((current_price - buy_price) / buy_price) * 100
                        total_pnl += pnl_percent
                        
                        if pnl_percent > 0:
                            profitable_positions += 1
                        else:
                            losing_positions += 1
                except:
                    continue
            
            # Portfolio performance alerts
            if total_positions > 0:
                avg_pnl = total_pnl / total_positions
                win_rate = (profitable_positions / total_positions) * 100
                
                # Significant portfolio loss alert
                if avg_pnl <= -10:
                    alert = {
                        'type': 'portfolio_loss',
                        'symbol': 'PORTFOLIO',
                        'message': f"📉 **PORTFOLIO ALERT**\n"
                                  f"Average Loss: {avg_pnl:.1f}%\n"
                                  f"Win Rate: {win_rate:.1f}%\n"
                                  f"🔍 Review positions for risk management",
                        'timestamp': datetime.now(),
                        'priority': 'HIGH'
                    }
                    alerts.append(alert)
                
                # Low win rate alert
                elif win_rate < 30:
                    alert = {
                        'type': 'low_winrate',
                        'symbol': 'PORTFOLIO',
                        'message': f"⚠️ **LOW WIN RATE ALERT**\n"
                                  f"Win Rate: {win_rate:.1f}%\n"
                                  f"Profitable: {profitable_positions}/{total_positions}\n"
                                  f"💡 Consider strategy review",
                        'timestamp': datetime.now(),
                        'priority': 'MEDIUM'
                    }
                    alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check portfolio alerts: {e}")
        
        return alerts