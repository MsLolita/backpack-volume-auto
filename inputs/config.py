THREADS = 1  # Enter amount of threads
DELAY_BETWEEN_TRADE = (1, 3)  # Execute delay between every trade (Buy -> Delay -> Sell -> Buy -> Delay ...)
DELAY_BETWEEN_DEAL = (0, 0)  # Execute delay between full trade (Buy -> Sell -> Delay -> Buy -> Sell -> Delay ...)

NEEDED_TRADE_VOLUME = 0  # volume to trade, if 0 it will never stop
MIN_BALANCE_TO_LEFT = 0  # min amount to left on the balance, if 0, it is traded until the balance is equal to 0.

TRADE_AMOUNT = [0, 0]  # minimum and maximum amount to trade in USD, if 0 it will trade on FULL balance
ALLOWED_ASSETS = ["BONK_USDC"]
















###################################### left empty
ACCOUNTS_FILE_PATH = "inputs/accounts.txt"
PROXIES_FILE_PATH = "inputs/proxies.txt"
