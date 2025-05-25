#!/usr/bin/env python3
"""
Binance Trading Bot Script with Simulated and Real Trading Modes

Requirements Implemented:
1. Mode switching (simulated vs real) using different API keys.
2. Queries Binance for the Top Gainers using the 24-hour ticker data (using BUY_TRIGGER threshold) via get_ticker().
3. Uses an INITIAL_WALLET variable for simulated trades.
4. Trades a fixed TRADE_AMOUNT per coin.
5. Periodically queries the coins held every 5 minutes.
6. Sells coins when profit exceeds SELL_PROFIT_TRIGGER or loss exceeds SELL_LOSS_TRIGGER.
7. When a coin is sold, queries for new top gainers and purchases until 5 positions are held.
8. Fully commented for debugging.
9. Logs trading actions, wallet, and positions in a Tkinter GUI.
10. Start and Stop trading functionality in the GUI.
11. Outputs detailed logs to a log file for historical debugging.

Remember: In real mode, use proper API keys. Always test in simulated mode first.
"""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time
import datetime
import logging

# Import Binance Client and exceptions from python-binance.
from binance.client import Client
from binance.exceptions import BinanceAPIException

####################
# CONFIGURATION
####################

# Choose mode: set to "simulated" for testing (READ ONLY API keys) or "real" for live trading.
TRADING_MODE = "simulated"  # Change to "real" to trade live

# API keys – be sure to replace with your own keys.
# For simulated mode, it is recommended to use READ-ONLY keys.
API_KEY = "YOUR_REAL_API_KEY_HERE"
API_SECRET = "YOUR_REAL_API_SECRET_HERE"

# Read-only keys for simulation mode.
READ_ONLY_API_KEY = "API KEY"
READ_ONLY_API_SECRET = "API SECRET"

# Trade parameters (you can easily adjust these values)
BUY_TRIGGER = 6.0         # Percentage increase required to trigger a buy (from Binance 24h change)
INITIAL_WALLET = 200.0   # Starting wallet balance in USDT (for simulation)
TRADE_AMOUNT = 10.0      # Amount in USDT allocated per trade
SELL_PROFIT_TRIGGER = 3.0 # Sell when profit exceeds 5%
SELL_LOSS_TRIGGER = -3.0  # Sell when loss exceeds -3%

# Logging configuration: all logs are written to "trading_bot.log"
logging.basicConfig(
    filename="trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

####################
# TRADING BOT CLASS
####################

class TradingBot:
    def __init__(self, log_callback):
        """
        Initialize the trading bot.
        
        Args:
            log_callback (function): A callback function to display logs in the GUI.
        """
        self.log_callback = log_callback   # Callback to send messages to the GUI log
        self.trading_active = False        # Flag to control the trading loop
        self.positions = {}                # Dictionary to track positions: {symbol: {buy_price, quantity, timestamp}}
        self.wallet = INITIAL_WALLET       # Starting wallet balance (simulation)
        
        # Create the Binance client based on the trading mode.
        if TRADING_MODE.lower() == "simulated":
            self.client = Client(READ_ONLY_API_KEY, READ_ONLY_API_SECRET)
            self.log("Initialized Binance client in SIMULATED mode (read-only keys).")
        else:
            self.client = Client(API_KEY, API_SECRET)
            self.log("Initialized Binance client in REAL trading mode.")

    def log(self, message):
        """
        Log a message both to the log file and via the GUI callback.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        logging.info(full_message)
        self.log_callback(full_message)

    def get_top_gainers(self):
        """
        Query Binance for USDT pairs based on their 24-hour price-change data.
        Only those coins with a percentage increase over BUY_TRIGGER are returned,
        sorted from highest to lowest gain.
        
        Returns:
            A list of dictionaries with keys: 'symbol', 'change_pct', 'current_price'
        """
        self.log("Querying top gainers using Binance 24hr ticker data.")
        gainers = []
        try:
            # Use get_ticker() to retrieve the 24-hour statistics for all symbols.
            tickers = self.client.get_ticker()  # This call returns the list of tickers with 24h data.
        except Exception as e:
            self.log(f"Error fetching 24hr ticker data: {str(e)}")
            return gainers
        
        # Filter for USDT pairs and check if the 24h percentage change meets the trigger.
        for ticker in tickers:
            symbol = ticker['symbol']
            if not symbol.endswith("USDT"):
                continue
            try:
                change_pct = float(ticker['priceChangePercent'])
                if change_pct >= BUY_TRIGGER:
                    current_price = float(ticker['lastPrice'])
                    gainers.append({'symbol': symbol, 'change_pct': change_pct, 'current_price': current_price})
            except Exception as e:
                self.log(f"Error processing ticker for {symbol}: {str(e)}")
                continue
        
        # Sort the gainers by percentage change and return the top 5.
        gainers.sort(key=lambda x: x['change_pct'], reverse=True)
        top_5 = gainers[:5]
        self.log("Top gainers: " + ", ".join([f"{g['symbol']} ({round(g['change_pct'],2)}%)" for g in top_5]))
        return top_5

    def execute_buy(self, symbol, price):
        """
        Execute a buy order for a given symbol at a provided price.
        
        In SIMULATED mode, adjust the wallet and store the position locally.
        In REAL mode, send a market order to Binance.
        """
        if TRADING_MODE.lower() == "simulated" and self.wallet < TRADE_AMOUNT:
            self.log(f"Not enough wallet balance to buy {symbol}.")
            return False

        self.log(f"Attempting to BUY {symbol} at {price:.4f} USDT.")
        if TRADING_MODE.lower() == "simulated":
            # Calculate the quantity purchased based on TRADE_AMOUNT.
            quantity = TRADE_AMOUNT / price
            self.wallet -= TRADE_AMOUNT
            self.positions[symbol] = {
                'buy_price': price,
                'quantity': quantity,
                'timestamp': datetime.datetime.now()
            }
            self.log(f"Simulated BUY: {symbol} - Quantity: {quantity:.6f} at Price: {price:.4f} USDT. New wallet balance: {self.wallet:.2f} USDT.")
            return True
        else:
            try:
                # Place a real market buy order using the USDT amount.
                order = self.client.order_market_buy(
                    symbol=symbol,
                    quoteOrderQty=TRADE_AMOUNT
                )
                executed_price = float(order['fills'][0]['price'])
                quantity = float(order['executedQty'])
                self.positions[symbol] = {
                    'buy_price': executed_price,
                    'quantity': quantity,
                    'timestamp': datetime.datetime.now()
                }
                self.log(f"REAL BUY: {symbol} - Purchased {quantity:.6f} at {executed_price:.4f} USDT.")
                return True
            except BinanceAPIException as e:
                self.log(f"Binance API error during BUY for {symbol}: {str(e)}")
                return False
            except Exception as e:
                self.log(f"Error during BUY for {symbol}: {str(e)}")
                return False

    def execute_sell(self, symbol, price):
        """
        Execute a sell order for a held position at the provided price.
        
        In SIMULATED mode, update the wallet and remove the position.
        In REAL mode, send a market sell order to Binance.
        """
        if symbol not in self.positions:
            self.log(f"No open position found for {symbol} to sell.")
            return False

        position = self.positions[symbol]
        self.log(f"Attempting to SELL {symbol} at {price:.4f} USDT.")
        if TRADING_MODE.lower() == "simulated":
            proceeds = position['quantity'] * price
            profit_loss = proceeds - (position['quantity'] * position['buy_price'])
            self.wallet += proceeds
            self.log(f"Simulated SELL: {symbol} - Sold {position['quantity']:.6f} at {price:.4f} USDT. P/L: {profit_loss:.2f} USDT. New wallet balance: {self.wallet:.2f} USDT.")
            del self.positions[symbol]
            return True
        else:
            try:
                order = self.client.order_market_sell(
                    symbol=symbol,
                    quantity=position['quantity']
                )
                executed_price = float(order['fills'][0]['price'])
                proceeds = position['quantity'] * executed_price
                profit_loss = proceeds - (position['quantity'] * position['buy_price'])
                self.log(f"REAL SELL: {symbol} - Sold {position['quantity']:.6f} at {executed_price:.4f} USDT. P/L: {profit_loss:.2f} USDT.")
                del self.positions[symbol]
                return True
            except BinanceAPIException as e:
                self.log(f"Binance API error during SELL for {symbol}: {str(e)}")
                return False
            except Exception as e:
                self.log(f"Error during SELL for {symbol}: {str(e)}")
                return False

    def update_positions(self):
        """
        For each held position, query the current price and if either the profit or loss threshold is met,
        execute a sell order.
        """
        symbols_to_sell = []
        for symbol, position in self.positions.items():
            try:
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                buy_price = position['buy_price']
                change_pct = ((current_price - buy_price) / buy_price) * 100.0
                self.log(f"{symbol} - Buy: {buy_price:.4f} USDT, Current: {current_price:.4f} USDT, Change: {change_pct:.2f}%")
                if change_pct >= SELL_PROFIT_TRIGGER or change_pct <= SELL_LOSS_TRIGGER:
                    symbols_to_sell.append((symbol, current_price, change_pct))
            except Exception as e:
                self.log(f"Error updating position for {symbol}: {str(e)}")
        for symbol, price, change_pct in symbols_to_sell:
            self.log(f"Sell condition met for {symbol} (Change: {change_pct:.2f}%). Executing sell.")
            self.execute_sell(symbol, price)

    def trading_loop(self):
        """
        The main trading loop:
          - Updates open positions every 5 minutes.
          - Checks symbol sell conditions.
          - If fewer than 5 positions are held, queries for new coins (using top gainers) and executes buy orders.
        """
        self.trading_active = True
        self.log("Trading loop started.")
        while self.trading_active:
            loop_start = time.time()
            
            # Update positions: evaluate if any position should be sold.
            self.update_positions()
            
            # If fewer than 5 positions, query for new coins to purchase.
            if len(self.positions) < 5:
                top_gainers = self.get_top_gainers()
                for coin in top_gainers:
                    if coin['symbol'] not in self.positions and len(self.positions) < 5:
                        self.execute_buy(coin['symbol'], coin['current_price'])
            
            # Log current wallet balance and positions.
            self.log(f"Wallet balance: {self.wallet:.2f} USDT")
            pos_list = [(s, self.positions[s]['buy_price']) for s in self.positions]
            self.log(f"Open positions: {pos_list}")
            
            # Sleep until the next 5-minute cycle.
            elapsed = time.time() - loop_start
            for _ in range(max(0, int(300 - elapsed))):
                if not self.trading_active:
                    break
                time.sleep(1)
        
            # End of cycle loop.
        self.log("Trading loop stopped.")

    def stop(self):
        """
        Stops the trading loop.
        """
        self.trading_active = False

####################
# GUI APPLICATION CLASS
####################

class GUIApp:
    def __init__(self, root):
        """
        Initialize the GUI widgets and create an instance of the trading bot.
        """
        self.root = root
        self.root.title("Binance Trading Bot")
        self.create_widgets()
        self.bot = TradingBot(self.write_log)
        self.trading_thread = None
        self.update_positions_table()

    def create_widgets(self):
        """
        Create GUI components: buttons, scrolling text for logs, and a table for positions.
        """
        button_frame = tk.Frame(self.root)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.start_button = tk.Button(button_frame, text="Start", command=self.start_trading)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_trading, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.log_text = ScrolledText(self.root, height=15, state=tk.DISABLED)
        self.log_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(self.root, columns=("Symbol", "Buy Price", "Quantity", "Current Price", "Change %"),
                                 show="headings")
        self.tree.heading("Symbol", text="Symbol")
        self.tree.heading("Buy Price", text="Buy Price")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Current Price", text="Current Price")
        self.tree.heading("Change %", text="Change %")
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def write_log(self, message):
        """
        Write log messages to the GUI.
        """
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.yview(tk.END)

    def start_trading(self):
        """
        Start the trading bot in a separate thread.
        """
        self.write_log("Starting trading bot...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.bot = TradingBot(self.write_log)
        self.trading_thread = threading.Thread(target=self.bot.trading_loop, daemon=True)
        self.trading_thread.start()

    def stop_trading(self):
        """
        Stop the trading bot gracefully.
        """
        self.write_log("Stopping trading bot...")
        self.bot.stop()
        if self.trading_thread is not None:
            self.trading_thread.join(timeout=10)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.write_log("Trading bot stopped.")

    def update_positions_table(self):
        """
        Update the positions table with current positions and their latest values.
        """
        for row in self.tree.get_children():
            self.tree.delete(row)
        for symbol, position in self.bot.positions.items():
            try:
                ticker = self.bot.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                change_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100.0
                self.tree.insert("", tk.END, values=(
                    symbol,
                    f"{position['buy_price']:.4f}",
                    f"{position['quantity']:.6f}",
                    f"{current_price:.4f}",
                    f"{change_pct:.2f}%"
                ))
            except Exception as e:
                self.tree.insert("", tk.END, values=(
                    symbol,
                    f"{position['buy_price']:.4f}",
                    f"{position['quantity']:.6f}",
                    "N/A",
                    "N/A"
                ))
        self.root.after(10000, self.update_positions_table)

####################
# MAIN: Launch the GUI Application
####################

if __name__ == "__main__":
    root = tk.Tk()
    app = GUIApp(root)
    root.mainloop()
