# SageCryBotv1 - Automated Crypto Trading Bot

SageCryBotv1 is a Python-based trading bot that interacts with the Binance cryptocurrency exchange. It features both simulated and real trading modes, allowing users to test strategies or engage in live trading. Configuration is handled entirely through a graphical user interface (GUI).

## ⚠️ IMPORTANT: Risk Disclaimer ⚠️

**Trading cryptocurrencies involves significant risk of financial loss. This bot is provided "as-is" without any warranties, and its use is entirely at your own risk.**

*   **You are solely responsible for any financial losses incurred.** The creators or contributors of this bot cannot be held liable for any losses resulting from its use.
*   **Thorough Testing Recommended:** Always test the bot extensively in **simulated mode** with various settings and market conditions before considering real trading. Understand its behavior and limitations.
*   **API Key Security:**
    *   You are responsible for the security of your API keys.
    *   For **simulated mode**, it is strongly recommended to use read-only API keys if you connect it to your real Binance account for market data.
    *   For **real trading**, ensure your API keys have the minimum necessary permissions (e.g., enable spot trading, disable withdrawals if not needed).
    *   **Never share your API keys or commit them to public repositories.** This application loads API keys into memory for the session and does **not** save them to disk.
*   **No Guarantees:** Past performance is not indicative of future results. There is no guarantee that this bot will generate profits. Market conditions can change rapidly.
*   **Use with Caution:** Understand the code and its logic before using it with real funds.

## Features

*   **GUI-Based Configuration:** All settings, including API keys and trading parameters, are configured through an easy-to-use graphical interface.
*   **Trading Modes:**
    *   **Simulated Mode:** Trades with a virtual wallet, allowing risk-free testing and strategy evaluation using real-time market data (requires read-only API keys).
    *   **Real Mode:** Executes live trades on your Binance account (requires trading-enabled API keys).
*   **Top Gainer Strategy:** Identifies potential trading opportunities by querying Binance for top gainers based on 24-hour price change percentage.
*   **Dynamic Position Management:**
    *   Aims to hold up to a configurable number of positions (default is 5).
    *   Automatically buys new coins if the number of open positions is below the maximum.
*   **Profit/Loss Triggers:** Sells positions based on configurable percentage-based profit or loss triggers.
*   **Session-Based Operation:** API keys and configuration are held in memory for the current session only and are not stored on disk.
*   **Real-time Logging:** Trading actions, wallet status, and position updates are logged to both the GUI and a `trading_bot.log` file.
*   **Active Configuration Display:** Shows the currently active trading parameters in the GUI once the bot is started.

## Setup and Installation

1.  **Prerequisites:**
    *   Python 3.7+
    *   `pip` (Python package installer)

2.  **Clone the Repository (Optional):**
    If you have git, you can clone the repository. Otherwise, download the `SageCryBotv1.py` and `requirements.txt` files.
    ```bash
    # git clone <repository_url> # Replace with actual URL if applicable
    # cd <repository_directory>
    ```

3.  **Install Dependencies:**
    Navigate to the directory containing `requirements.txt` and run:
    ```bash
    pip install -r requirements.txt
    ```
    This will install the necessary `python-binance` library.

## Configuration

All configuration is done through the GUI when you run the bot. No manual code editing is required for settings.

**Configuration Fields:**

*   **Trading Mode:**
    *   `simulated`: For paper trading with a virtual wallet.
    *   `real`: For live trading with actual funds.
*   **API Keys:**
    *   **Real API Key / Secret:** Your Binance API key and secret with trading permissions. Required for "real" mode.
    *   **Read-Only API Key / Secret:** Your Binance API key and secret with only read permissions. Required for "simulated" mode to fetch market data.
    *   *Note: API keys are shown with asterisks (`*`) for the secret key in the input fields for basic privacy.*
*   **Trading Parameters (all percentage values are entered as numbers, e.g., 5 for 5%):**
    *   **Buy Trigger (%):** The minimum 24-hour price change percentage for a coin to be considered a top gainer and trigger a potential buy.
    *   **Initial Wallet (USDT):** The starting USDT balance for simulated mode. (This field is disabled in "real" mode).
    *   **Trade Amount (USDT):** The amount of USDT to use for each individual trade.
    *   **Sell Profit Trigger (%):** The percentage increase from the buy price at which to sell a coin for profit.
    *   **Sell Loss Trigger (%):** The percentage decrease from the buy price at which to sell a coin to limit losses (should be a negative value, e.g., -3 for -3%).

**API Key Handling:**
The API keys you enter are held in the application's memory only for the duration of the current session. They are **not** saved to any file on your computer by this application. You will need to re-enter them each time you start the bot.

## How to Run

1.  Ensure you have completed the Setup and Installation steps.
2.  Open a terminal or command prompt.
3.  Navigate to the directory where `SageCryBotv1.py` is located.
4.  Run the script:
    ```bash
    python SageCryBotv1.py
    ```
5.  The GUI will open. Fill in all the configuration fields as described above.
6.  Click **"Start Trading"**.
7.  Monitor the bot's actions in the "Log" area and the "Positions Table".
8.  To stop the bot, click **"Stop Trading"**. The bot will attempt to finish any immediate pending actions and then halt the trading loop.

## Logging

*   **GUI Log:** The main application window has a scrolled text area that displays live log messages from the bot.
*   **File Log:** All log messages are also saved to `trading_bot.log` in the same directory as the script. This file provides a persistent record of trading activities for review and debugging.

## Disclaimer

This bot is for educational and experimental purposes. Trading cryptocurrencies is highly speculative and carries a high risk of loss. Use this software responsibly and at your own risk. See the full risk disclaimer at the top of this document.
