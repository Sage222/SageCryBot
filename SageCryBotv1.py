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
12. GUI-based configuration for all trading parameters and API keys.

Remember: In real mode, use proper API keys. Always test in simulated mode first.
"""

import tkinter as tk
from tkinter import ttk, font
from tkinter.scrolledtext import ScrolledText
import threading
import time
import datetime
import logging

# Import Binance Client and exceptions from python-binance.
from binance.client import Client
from binance.exceptions import BinanceAPIException

####################
# CONFIGURATION (Now primarily through GUI)
####################

# --- Application Constants ---
# Logging
LOG_FILENAME = "trading_bot.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Trading Modes
MODE_SIMULATED = "simulated"
MODE_REAL = "real"

# Default GUI Values for API Keys & Parameters
DEFAULT_REAL_API_KEY = "YOUR_REAL_API_KEY_HERE"
DEFAULT_REAL_API_SECRET = "YOUR_REAL_API_SECRET_HERE"
DEFAULT_READONLY_API_KEY = "API KEY"
DEFAULT_READONLY_API_SECRET = "API SECRET" # Intentionally different from above for clarity
DEFAULT_BUY_TRIGGER_PERCENT = "6.0"
DEFAULT_INITIAL_WALLET_USDT = "200.0"
DEFAULT_TRADE_AMOUNT_USDT = "10.0"
DEFAULT_SELL_PROFIT_TRIGGER_PERCENT = "3.0"
DEFAULT_SELL_LOSS_TRIGGER_PERCENT = "-3.0"

# Trading Logic Parameters
TRADING_LOOP_CYCLE_SECONDS = 300
MAX_OPEN_POSITIONS = 5
USDT_SUFFIX = "USDT" # For symbol filtering and display

# GUI Messages & Placeholders
CLIENT_INIT_FAILURE_MESSAGE = "STOPPED_CLIENT_INIT_FAILURE"
API_KEY_DISPLAY_TRUNCATE_LENGTH = 5 # For obfuscating API key in display
PLACEHOLDER_NA = "N/A"
PLACEHOLDER_ERROR = "Error"

# GUI Specific Constants
WINDOW_TITLE = "SageCryBot v1 - GUI Config"
CONFIG_FRAME_TITLE = "Configuration"
ACTIVE_CONFIG_FRAME_TITLE = "Active Session Configuration"
# Treeview Columns
COLUMN_SYMBOL = "Symbol"
COLUMN_BUY_PRICE = "Buy Price"
COLUMN_QUANTITY = "Quantity"
COLUMN_CURRENT_PRICE = "Current Price"
COLUMN_CHANGE_PERCENT = "Change %"
# Default Sizes
DEFAULT_FONT_SIZE = 9
LOG_AREA_HEIGHT = 10 # in lines
POSITIONS_TABLE_HEIGHT = 6 # in lines
# Parameter Labels (used as keys and display text)
LABEL_TRADING_MODE = "Trading Mode:"
LABEL_REAL_API_KEY = "Real API Key:"
LABEL_REAL_API_SECRET = "Real API Secret:"
LABEL_READONLY_API_KEY = "Read-Only API Key:"
LABEL_READONLY_API_SECRET = "Read-Only API Secret:"
LABEL_BUY_TRIGGER = "Buy Trigger (%):"
LABEL_INITIAL_WALLET = "Initial Wallet (USDT):"
LABEL_TRADE_AMOUNT = "Trade Amount (USDT):"
LABEL_SELL_PROFIT_TRIGGER = "Sell Profit Trigger (%):"
LABEL_SELL_LOSS_TRIGGER = "Sell Loss Trigger (%):"
LABEL_API_KEY_USED = "API Key Used:" # For active config display

# --- End Application Constants ---

# Logging configuration
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format=LOG_FORMAT
)

####################
# TRADING BOT CLASS
####################

class TradingBot:
    def __init__(self, log_callback, api_key, api_secret, trading_mode,
                 buy_trigger, initial_wallet, trade_amount,
                 sell_profit_trigger, sell_loss_trigger):
        """
        Initialize the trading bot with configuration parameters.
        """
        self.log_callback = log_callback
        self.api_key = api_key
        self.api_secret = api_secret
        self.trading_mode = trading_mode.lower()
        self.buy_trigger = buy_trigger
        self.initial_wallet = initial_wallet
        self.trade_amount = trade_amount
        self.sell_profit_trigger = sell_profit_trigger
        self.sell_loss_trigger = sell_loss_trigger

        self.trading_active = False
        self.positions = {} # {symbol: {buy_price, quantity, timestamp}}
        self.wallet = 0.0

        if self.trading_mode == MODE_SIMULATED:
            self.wallet = self.initial_wallet
        
        self.client = None
        try:
            self.client = Client(self.api_key, self.api_secret)
            self.client.ping() # Test connection
            self.log(f"Successfully initialized Binance client in {self.trading_mode.upper()} mode.")
            if self.trading_mode == MODE_SIMULATED:
                self.log(f"Simulated mode: Initial wallet set to {self.wallet:.2f} USDT.")
            # In real mode, wallet balance is managed by Binance. We could fetch it if needed:
            # else:
            #     account_info = self.client.get_account()
            #     for balance in account_info['balances']:
            #         if balance['asset'] == 'USDT':
            #             self.wallet = float(balance['free'])
            #             self.log(f"Real mode: Fetched USDT wallet balance: {self.wallet:.2f} USDT")
            #             break
        except BinanceAPIException as e:
            self.log(f"Binance API Exception during client initialization: {e}")
            self.client = None # Critical error, bot cannot function
        except Exception as e: # Handles other errors like requests.exceptions.ConnectionError
            self.log(f"Error initializing Binance client: {str(e)}")
            self.client = None # Critical error, bot cannot function


    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        logging.info(full_message)
        if callable(self.log_callback):
            self.log_callback(full_message)

    def get_top_gainers(self):
        self.log("[GAINER_SCAN] Querying top gainers using Binance 24hr ticker data.")
        gainers = []
        if not self.client: return gainers
        try:
            tickers = self.client.get_ticker()
        except Exception as e:
            self.log(f"[GAINER_SCAN_ERROR] Error fetching 24hr ticker data: {str(e)}")
            return gainers
        
        for ticker in tickers:
            symbol = ticker['symbol']
            if not symbol.endswith(USDT_SUFFIX):
                continue
            try:
                change_pct = float(ticker['priceChangePercent'])
                if change_pct >= self.buy_trigger:
                    current_price = float(ticker['lastPrice'])
                    gainers.append({'symbol': symbol, 'change_pct': change_pct, 'current_price': current_price})
            except Exception as e:
                self.log(f"[GAINER_SCAN_ERROR] Error processing ticker for {symbol}: {str(e)}")
                continue
        
        gainers.sort(key=lambda x: x['change_pct'], reverse=True)
        top_5 = gainers[:5]
        self.log("[GAINER_SCAN_RESULT] Top gainers: " + ", ".join([f"{g['symbol']} ({round(g['change_pct'],2)}%)" for g in top_5]))
        return top_5

    def execute_buy(self, symbol, price):
        if not self.client: return False
        prefix = "[BUY_SIM]" if self.trading_mode == MODE_SIMULATED else "[BUY_REAL]"

        if self.trading_mode == MODE_SIMULATED and self.wallet < self.trade_amount:
            self.log(f"{prefix} [FAIL_INSUFFICIENT_FUNDS] Not enough wallet balance ({self.wallet:.2f} USDT) to buy {self.trade_amount:.2f} USDT of {symbol}.")
            return False

        self.log(f"{prefix} [ATTEMPT] Attempting to BUY {self.trade_amount:.2f} USDT of {symbol} at {price:.4f} USDT.")
        if self.trading_mode == MODE_SIMULATED:
            quantity = self.trade_amount / price
            self.wallet -= self.trade_amount
            self.positions[symbol] = {
                'buy_price': price, 'quantity': quantity, 'timestamp': datetime.datetime.now()
            }
            self.log(f"{prefix} [SUCCESS] {symbol} - Qty: {quantity:.6f} at Price: {price:.4f}. New Wallet: {self.wallet:.2f} USDT.")
            return True
        else: # Real mode
            try:
                order = self.client.order_market_buy(symbol=symbol, quoteOrderQty=self.trade_amount)
                executed_price = float(order['fills'][0]['price'])
                quantity = float(order['executedQty'])
                self.positions[symbol] = {
                    'buy_price': executed_price, 'quantity': quantity, 'timestamp': datetime.datetime.now()
                }
                self.log(f"{prefix} [SUCCESS] {symbol} - Purchased {quantity:.6f} at {executed_price:.4f} USDT.")
                return True
            except BinanceAPIException as e:
                self.log(f"{prefix} [FAIL_API_ERROR] Binance API error for {symbol}: {str(e)}")
                return False
            except Exception as e:
                self.log(f"{prefix} [FAIL_GENERAL_ERROR] Error for {symbol}: {str(e)}")
                return False

    def execute_sell(self, symbol, price):
        if not self.client: return False
        prefix = "[SELL_SIM]" if self.trading_mode == MODE_SIMULATED else "[SELL_REAL]"

        if symbol not in self.positions:
            self.log(f"{prefix} [FAIL_NO_POSITION] No open position found for {symbol} to sell.")
            return False

        position = self.positions[symbol]
        self.log(f"{prefix} [ATTEMPT] Attempting to SELL {position['quantity']:.6f} {symbol} at {price:.4f} USDT.")
        if self.trading_mode == MODE_SIMULATED:
            proceeds = position['quantity'] * price
            profit_loss = proceeds - (position['quantity'] * position['buy_price'])
            self.wallet += proceeds
            self.log(f"{prefix} [SUCCESS] {symbol} - Sold at {price:.4f}. P/L: {profit_loss:.2f} USDT. New Wallet: {self.wallet:.2f} USDT.")
            del self.positions[symbol]
            return True
        else: # Real mode
            try:
                order = self.client.order_market_sell(symbol=symbol, quantity=position['quantity'])
                executed_price = float(order['fills'][0]['price'])
                proceeds = float(order['cummulativeQuoteQty']) 
                profit_loss = proceeds - (position['quantity'] * position['buy_price'])
                self.log(f"{prefix} [SUCCESS] {symbol} - Sold {position['quantity']:.6f} at {executed_price:.4f} USDT. P/L: {profit_loss:.2f} USDT.")
                del self.positions[symbol]
                return True
            except BinanceAPIException as e:
                self.log(f"{prefix} [FAIL_API_ERROR] Binance API error for {symbol}: {str(e)}")
                return False
            except Exception as e:
                self.log(f"{prefix} [FAIL_GENERAL_ERROR] Error for {symbol}: {str(e)}")
                return False

    def update_positions(self):
        if not self.client: return
        self.log("[POSITION_CHECKS_START] Starting update and check of open positions.")
        symbols_to_sell = []
        for symbol, position in list(self.positions.items()): 
            try:
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                buy_price = position['buy_price']
                change_pct = ((current_price - buy_price) / buy_price) * 100.0
                self.log(f"[POSITION_STATUS] {symbol} - Buy: {buy_price:.4f}, Current: {current_price:.4f}, Change: {change_pct:.2f}%")
                if change_pct >= self.sell_profit_trigger or change_pct <= self.sell_loss_trigger:
                    symbols_to_sell.append((symbol, current_price, change_pct))
            except Exception as e:
                self.log(f"[POSITION_ERROR] Error updating position for {symbol}: {str(e)}")
        
        for symbol, price, change_pct in symbols_to_sell:
            self.log(f"[SELL_TRIGGERED] Sell condition met for {symbol} (Change: {change_pct:.2f}%). Executing sell.")
            self.execute_sell(symbol, price)
        self.log("[POSITION_CHECKS_END] Finished update and check of open positions.")


    def trading_loop(self):
        if not self.client:
            self.log("[CRITICAL_ERROR] Trading loop cannot start: Binance client not initialized.")
            self.trading_active = False 
            if callable(self.log_callback):
                 self.log_callback(CLIENT_INIT_FAILURE_MESSAGE) 
            return

        self.log("[CORE] Trading loop started.")
        while self.trading_active:
            loop_start_time = time.time()
            
            self.update_positions()
            
            if len(self.positions) < MAX_OPEN_POSITIONS: 
                top_gainers = self.get_top_gainers()
                for coin in top_gainers:
                    if len(self.positions) >= MAX_OPEN_POSITIONS: break
                    if coin['symbol'] not in self.positions:
                        self.execute_buy(coin['symbol'], coin['current_price'])
            
            if self.trading_mode == MODE_SIMULATED:
                self.log(f"[WALLET_SIM] Current Wallet (Simulated): {self.wallet:.2f} USDT")
            
            pos_summary = [f"{s} (Buy: {p['buy_price']:.4f})" for s, p in self.positions.items()]
            self.log(f"[POSITIONS_SUMMARY] Open positions ({len(self.positions)}): {', '.join(pos_summary) if pos_summary else 'None'}")
            
            elapsed_time = time.time() - loop_start_time
            sleep_duration = max(0, TRADING_LOOP_CYCLE_SECONDS - elapsed_time) # Target cycle
            
            # Sleep in 1s intervals to allow quick exit if stop signal is received
            for _ in range(int(sleep_duration)): 
                if not self.trading_active:
                    break
                time.sleep(1)
        
        self.log("[CORE] Trading loop stopped.")

    def stop(self):
        self.log("[CORE] Received stop signal.")
        self.trading_active = False

####################
# GUI APPLICATION CLASS
####################

class GUIApp:
    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title(WINDOW_TITLE)
        self.bot = None
        self.trading_thread = None
        self.config_widgets = [] # To store config entry/combobox widgets
        self.active_config_labels = {} # To store labels displaying active config

        self.create_widgets()
        self.update_active_config_display(running=False) # Initialize active config display
        self.update_positions_table() # Start periodic table updates

    def create_widgets(self):
        # Default font
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=DEFAULT_FONT_SIZE)
        self.root.option_add("*Font", default_font)

        # --- Configuration Frame ---
        config_frame = tk.LabelFrame(self.root, text=CONFIG_FRAME_TITLE, padx=10, pady=10)
        config_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        config_frame.columnconfigure(1, weight=1) # Make entry column expandable

        # Trading Mode
        tk.Label(config_frame, text=LABEL_TRADING_MODE).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.trading_mode_var = tk.StringVar(value=MODE_SIMULATED)
        self.trading_mode_combo = ttk.Combobox(config_frame, textvariable=self.trading_mode_var, values=[MODE_SIMULATED, MODE_REAL], state="readonly", width=47)
        self.trading_mode_combo.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.trading_mode_combo.bind("<<ComboboxSelected>>", self.toggle_initial_wallet_state)
        self.config_widgets.append(self.trading_mode_combo)

        # API Keys
        tk.Label(config_frame, text=LABEL_REAL_API_KEY).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.real_api_key_var = tk.StringVar(value=DEFAULT_REAL_API_KEY)
        real_api_key_entry = tk.Entry(config_frame, textvariable=self.real_api_key_var)
        real_api_key_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.config_widgets.append(real_api_key_entry)

        tk.Label(config_frame, text=LABEL_REAL_API_SECRET).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.real_api_secret_var = tk.StringVar(value=DEFAULT_REAL_API_SECRET)
        real_api_secret_entry = tk.Entry(config_frame, textvariable=self.real_api_secret_var, show="*")
        real_api_secret_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        self.config_widgets.append(real_api_secret_entry)

        tk.Label(config_frame, text=LABEL_READONLY_API_KEY).grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.readonly_api_key_var = tk.StringVar(value=DEFAULT_READONLY_API_KEY) 
        readonly_api_key_entry = tk.Entry(config_frame, textvariable=self.readonly_api_key_var)
        readonly_api_key_entry.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        self.config_widgets.append(readonly_api_key_entry)

        tk.Label(config_frame, text=LABEL_READONLY_API_SECRET).grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.readonly_api_secret_var = tk.StringVar(value=DEFAULT_READONLY_API_SECRET) 
        readonly_api_secret_entry = tk.Entry(config_frame, textvariable=self.readonly_api_secret_var, show="*")
        readonly_api_secret_entry.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=2)
        self.config_widgets.append(readonly_api_secret_entry)

        # Trading Parameters
        self.param_gui_setup = [ # List of tuples: (Label Text Constant, Default Value Constant)
            (LABEL_BUY_TRIGGER, DEFAULT_BUY_TRIGGER_PERCENT),
            (LABEL_INITIAL_WALLET, DEFAULT_INITIAL_WALLET_USDT),
            (LABEL_TRADE_AMOUNT, DEFAULT_TRADE_AMOUNT_USDT),
            (LABEL_SELL_PROFIT_TRIGGER, DEFAULT_SELL_PROFIT_TRIGGER_PERCENT),
            (LABEL_SELL_LOSS_TRIGGER, DEFAULT_SELL_LOSS_TRIGGER_PERCENT)
        ]
        self.param_vars = {} # Store StringVars, keyed by label_text_constant for access

        for i, (label_text_constant, default_value_constant) in enumerate(self.param_gui_setup):
            tk.Label(config_frame, text=label_text_constant).grid(row=5 + i, column=0, sticky=tk.W, padx=5, pady=2)
            var = tk.StringVar(value=default_value_constant)
            self.param_vars[label_text_constant] = var # Use the constant as key
            entry = tk.Entry(config_frame, textvariable=var)
            entry.grid(row=5 + i, column=1, sticky=tk.EW, padx=5, pady=2)
            self.config_widgets.append(entry)
            if label_text_constant == LABEL_INITIAL_WALLET:
                self.initial_wallet_entry = entry

        self.toggle_initial_wallet_state()

        # --- Control Buttons Frame ---
        button_frame = tk.Frame(self.root)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        self.start_button = tk.Button(button_frame, text="Start Trading", command=self.start_trading, width=15, height=1, bg="green", fg="white")
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = tk.Button(button_frame, text="Stop Trading", command=self.stop_trading, state=tk.DISABLED, width=15, height=1, bg="red", fg="white")
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # --- Active Configuration Display Frame ---
        active_config_frame = tk.LabelFrame(self.root, text=ACTIVE_CONFIG_FRAME_TITLE, padx=10, pady=10)
        active_config_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        active_config_frame.columnconfigure(1, weight=1)

        # These labels are used as keys in self.active_config_labels and for display
        self.active_config_display_labels = [ 
            LABEL_TRADING_MODE, LABEL_BUY_TRIGGER, LABEL_INITIAL_WALLET,
            LABEL_TRADE_AMOUNT, LABEL_SELL_PROFIT_TRIGGER, LABEL_SELL_LOSS_TRIGGER, 
            LABEL_API_KEY_USED
        ]
        self.active_config_labels = {} # Dictionary to store the value labels
        for i, label_text_constant in enumerate(self.active_config_display_labels):
            tk.Label(active_config_frame, text=label_text_constant).grid(row=i, column=0, sticky=tk.W, padx=5, pady=1)
            value_label = tk.Label(active_config_frame, text=PLACEHOLDER_NA, anchor="w")
            value_label.grid(row=i, column=1, sticky=tk.EW, padx=5, pady=1)
            self.active_config_labels[label_text_constant] = value_label # Use constant as key
            
        # --- Log Text Area ---
        self.log_text = ScrolledText(self.root, height=LOG_AREA_HEIGHT, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # --- Positions Table ---
        self.tree_columns = (COLUMN_SYMBOL, COLUMN_BUY_PRICE, COLUMN_QUANTITY, COLUMN_CURRENT_PRICE, COLUMN_CHANGE_PERCENT)
        self.tree = ttk.Treeview(self.root, columns=self.tree_columns, show="headings", height=POSITIONS_TABLE_HEIGHT)
        col_widths = {COLUMN_SYMBOL: 100, COLUMN_BUY_PRICE: 80, COLUMN_QUANTITY: 100, COLUMN_CURRENT_PRICE: 80, COLUMN_CHANGE_PERCENT: 70}
        for col_name in self.tree_columns:
            self.tree.heading(col_name, text=col_name)
            self.tree.column(col_name, width=col_widths.get(col_name, 80), anchor=tk.CENTER) # Default width 80
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

    def toggle_initial_wallet_state(self, event=None):
        if hasattr(self, 'initial_wallet_entry'):
            if self.trading_mode_var.get() == MODE_REAL:
                self.initial_wallet_entry.config(state=tk.DISABLED)
            else: # MODE_SIMULATED
                self.initial_wallet_entry.config(state=tk.NORMAL)
    
    def set_config_widgets_state(self, state):
        # state should be tk.NORMAL, tk.DISABLED, or "readonly" for combobox
        for widget in self.config_widgets:
            if isinstance(widget, ttk.Combobox):
                widget.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
            else:
                widget.config(state=state)
        self.toggle_initial_wallet_state() # Keep initial wallet consistent

    def write_log(self, message):
        if message == CLIENT_INIT_FAILURE_MESSAGE: 
            self.write_log("CRITICAL ERROR: Binance client failed to initialize. Trading stopped.")
            self.stop_trading(force_gui_reset=True) 
            return

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.yview(tk.END) # Auto-scroll

    def start_trading(self):
        self.write_log("Attempting to start trading bot...")
        try:
            # Retrieve and validate config
            trading_mode = self.trading_mode_var.get() # This will be MODE_SIMULATED or MODE_REAL
            real_api_key = self.real_api_key_var.get()
            real_api_secret = self.real_api_secret_var.get()
            readonly_api_key = self.readonly_api_key_var.get()
            readonly_api_secret = self.readonly_api_secret_var.get()
            
            # Retrieve parameters using the label text constants as keys
            buy_trigger = float(self.param_vars[LABEL_BUY_TRIGGER].get())
            initial_wallet_str = self.param_vars[LABEL_INITIAL_WALLET].get()
            initial_wallet = float(initial_wallet_str) if trading_mode == MODE_SIMULATED and initial_wallet_str else 0.0
            trade_amount = float(self.param_vars[LABEL_TRADE_AMOUNT].get())
            sell_profit_trigger = float(self.param_vars[LABEL_SELL_PROFIT_TRIGGER].get())
            sell_loss_trigger = float(self.param_vars[LABEL_SELL_LOSS_TRIGGER].get())

            # Basic Validation
            if trading_mode == MODE_REAL:
                if not real_api_key or real_api_key == DEFAULT_REAL_API_KEY or \
                   not real_api_secret or real_api_secret == DEFAULT_REAL_API_SECRET:
                    self.write_log(f"ERROR: Real API Key and Secret are required for '{MODE_REAL}' trading mode.")
                    return
                api_key_to_use, api_secret_to_use = real_api_key, real_api_secret
            else: # MODE_SIMULATED
                if not readonly_api_key or readonly_api_key == DEFAULT_READONLY_API_KEY or \
                   not readonly_api_secret or readonly_api_secret == DEFAULT_READONLY_API_SECRET:
                    self.write_log(f"ERROR: Read-Only API Key and Secret are required for '{MODE_SIMULATED}' mode.")
                    return
                api_key_to_use, api_secret_to_use = readonly_api_key, readonly_api_secret

            if trade_amount <= 0:
                self.write_log("ERROR: Trade Amount must be positive.")
                return
            if trading_mode == MODE_SIMULATED and initial_wallet < 0:
                 self.write_log(f"ERROR: Initial Wallet must be non-negative for {MODE_SIMULATED} mode.")
                 return
            if buy_trigger <= 0 or sell_profit_trigger <= 0:
                 self.write_log("ERROR: Buy and Sell Profit Triggers must be positive percentages.")
                 return
            if sell_loss_trigger >= 0:
                 self.write_log("ERROR: Sell Loss Trigger must be a negative percentage (e.g., -3.0).") # Example value matches default
                 return


        except ValueError as e:
            self.write_log(f"ERROR: Invalid input for a numerical field. Please check parameters. Details: {e}")
            return
        except Exception as e: # Catch-all for other unexpected validation errors
            self.write_log(f"ERROR: Unexpected error during configuration validation: {e}")
            return

        self.write_log("Configuration validated. Initializing and starting trading bot...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.set_config_widgets_state(tk.DISABLED)

        self.bot = TradingBot(
            log_callback=self.write_log,
            api_key=api_key_to_use, api_secret=api_secret_to_use, trading_mode=trading_mode,
            buy_trigger=buy_trigger, initial_wallet=initial_wallet, trade_amount=trade_amount,
            sell_profit_trigger=sell_profit_trigger, sell_loss_trigger=sell_loss_trigger
        )

        if self.bot.client is None: # Check if client initialization failed in TradingBot
            self.write_log("ERROR: TradingBot failed to initialize Binance client. Cannot start.")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.set_config_widgets_state(tk.NORMAL)
            self.update_active_config_display(running=False) # Clear active config
            return
        
        self.update_active_config_display(running=True) # Update display with active config

        self.trading_thread = threading.Thread(target=self.bot.trading_loop, daemon=True)
        self.trading_thread.start()

    def stop_trading(self, force_gui_reset=False): # Added param for special cases
        if not force_gui_reset: # Normal stop initiated by user
             self.write_log("Stopping trading bot...")
             if self.bot:
                self.bot.stop()

        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=10)
            if self.trading_thread.is_alive():
                self.write_log("Warning: Trading thread did not terminate gracefully.")
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.set_config_widgets_state(tk.NORMAL)
        if not force_gui_reset: # Avoid double logging if forced
            self.write_log("Trading bot stopped.")
        self.bot = None # Clear bot instance
        self.update_active_config_display(running=False) # Clear active config display

    def update_active_config_display(self, running=False):
        if running and self.bot:
            active_details = {
                LABEL_TRADING_MODE: self.bot.trading_mode.capitalize(),
                LABEL_BUY_TRIGGER: f"{self.bot.buy_trigger:.2f}",
                LABEL_INITIAL_WALLET: f"{self.bot.initial_wallet:.2f}" if self.bot.trading_mode == MODE_SIMULATED else f"{PLACEHOLDER_NA} (Real Mode)",
                LABEL_TRADE_AMOUNT: f"{self.bot.trade_amount:.2f}",
                LABEL_SELL_PROFIT_TRIGGER: f"{self.bot.sell_profit_trigger:.2f}",
                LABEL_SELL_LOSS_TRIGGER: f"{self.bot.sell_loss_trigger:.2f}",
                LABEL_API_KEY_USED: f"{self.bot.api_key[:API_KEY_DISPLAY_TRUNCATE_LENGTH]}...{self.bot.api_key[-API_KEY_DISPLAY_TRUNCATE_LENGTH:]}" if self.bot.api_key else PLACEHOLDER_NA
            }
        else:
            # Use self.active_config_display_labels to ensure all defined labels are reset
            active_details = {key: PLACEHOLDER_NA for key in self.active_config_display_labels}

        for key_constant, label_widget in self.active_config_labels.items(): # Iterates using constant keys
            label_widget.config(text=active_details.get(key_constant, PLACEHOLDER_ERROR))


    def update_positions_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        if self.bot and self.bot.client and self.bot.positions:
            for symbol, data in self.bot.positions.items():
                try:
                    ticker = self.bot.client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                    change_pct = ((current_price - data['buy_price']) / data['buy_price']) * 100.0
                    self.tree.insert("", tk.END, values=(
                        COLUMN_SYMBOL: symbol,
                        COLUMN_BUY_PRICE: f"{data['buy_price']:.4f}",
                        COLUMN_QUANTITY: f"{data['quantity']:.6f}",
                        COLUMN_CURRENT_PRICE: f"{current_price:.4f}",
                        COLUMN_CHANGE_PERCENT: f"{change_pct:.2f}%"
                    }
                    self.tree.insert("", tk.END, values=tuple(row_values[col] for col in self.tree_columns))
                except Exception as e:
                    # self.write_log(f"Error updating table for {symbol}: {e}") 
                    row_values = {
                        COLUMN_SYMBOL: symbol,
                        COLUMN_BUY_PRICE: f"{data.get('buy_price', 0):.4f}",
                        COLUMN_QUANTITY: f"{data.get('quantity', 0):.6f}",
                        COLUMN_CURRENT_PRICE: PLACEHOLDER_ERROR,
                        COLUMN_CHANGE_PERCENT: PLACEHOLDER_NA
                    }
                    self.tree.insert("", tk.END, values=tuple(row_values[col] for col in self.tree_columns))
        
        self.root.after(10000, self.update_positions_table) # Reschedule

####################
# MAIN: Launch the GUI Application
####################

if __name__ == "__main__":
    root = tk.Tk()
    app = GUIApp(root)
    root.mainloop()
