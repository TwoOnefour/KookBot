from __init__ import KookBot
import urllib3


if __name__ == "__main__":
    urllib3.disable_warnings()
    bot = KookBot()
    bot.connect()
