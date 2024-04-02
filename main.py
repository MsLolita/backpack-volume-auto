import asyncio
import ctypes
import sys

from core.autoreger import AutoReger
from core.backpack_trade import BackpackTrade

from art import text2art
from termcolor import colored, cprint

from core.utils import logger
from inputs.config import (ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, THREADS, DELAY_BETWEEN_TRADE, DELAY_BETWEEN_DEAL,
                           ALLOWED_ASSETS, NEEDED_TRADE_VOLUME, MIN_BALANCE_TO_LEFT, TRADE_AMOUNT, CONVERT_ALL_TO_USDC)


def bot_info(name: str = ""):
    cprint(text2art(name), 'green')

    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")

    print(
        f"{colored('EnJoYeR <crypto/> moves:', color='light_yellow')} "
        f"{colored('https://t.me/+tdC-PXRzhnczNDli', color='light_green')}"
    )
    print(
        f"{colored('To say thanks for work:', color='light_yellow')} "
        f"{colored('0x000007c73a94f8582ef95396918dcd04f806cdd8', color='light_green')}"
    )


async def worker_task(account: str, proxy: str):
    api_key, api_secret = account.split(":")

    try:
        backpack = BackpackTrade(api_key, api_secret, proxy, DELAY_BETWEEN_TRADE, DELAY_BETWEEN_DEAL,
                                 NEEDED_TRADE_VOLUME, MIN_BALANCE_TO_LEFT, TRADE_AMOUNT)
    except Exception as e:
        logger.error(f"WRONG API SECRET KEY !!!!!!!!!!!!!!!!!!!!!!!!: {e}")
        return False

    await backpack.show_balances()

    if CONVERT_ALL_TO_USDC:
        await backpack.sell_all()
    else:
        await backpack.start_trading(pairs=ALLOWED_ASSETS)

    await backpack.show_balances()

    await backpack.close()

    return True


async def main():
    bot_info("BACKPACK_AUTO")

    autoreger = AutoReger.get_accounts(ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH)
    await autoreger.start(worker_task, THREADS)


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
