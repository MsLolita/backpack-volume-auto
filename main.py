import asyncio
import ctypes
import sys

from core.autoreger import AutoReger
from core.backpack_trade import BackpackTrade
from art import tprint

from core.utils import logger
from inputs.config import (ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, THREADS, DELAY_BETWEEN_TRADE, DELAY_BETWEEN_DEAL,
                           ALLOWED_ASSETS, NEEDED_TRADE_VOLUME, MIN_BALANCE_TO_LEFT, TRADE_AMOUNT, CONVERT_ALL_TO_USDC)


def bot_info(name: str = ""):
    tprint(name)

    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")
    print("EnJoYeR's <crypto/> moves: https://t.me/+tdC-PXRzhnczNDli\n")


async def worker_task(account: str, proxy: str):
    api_key, api_secret = account.split(":")

    try:
        backpack = BackpackTrade(api_key, api_secret, proxy, DELAY_BETWEEN_TRADE, DELAY_BETWEEN_DEAL,
                                 NEEDED_TRADE_VOLUME, MIN_BALANCE_TO_LEFT, TRADE_AMOUNT)
    except Exception as e:
        logger.error(f"WRONG API SECRET KEY !!!!!!!!!!!!!!!!!!!!!!!!: {e}")
        return

    await backpack.show_balances()

    if CONVERT_ALL_TO_USDC:
        await backpack.sell_all()
    else:
        await backpack.start_trading(pairs=ALLOWED_ASSETS)

    await backpack.show_balances()

    await backpack.close()

    return True


async def main():
    bot_info("Backpack_Trading")

    autoreger = AutoReger.get_accounts(ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH)
    await autoreger.start(worker_task, THREADS)


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
