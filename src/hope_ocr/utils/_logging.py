import logging

from colorama import Fore

MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24


class LevelFormatter(logging.Formatter):
    template = f"$color$%(levelname)s{Fore.RESET}: {Fore.LIGHTWHITE_EX}%(name)s{Fore.RESET} - %(message)s"
    default = Fore.LIGHTWHITE_EX
    colors = {
        logging.DEBUG: Fore.MAGENTA,
        logging.CRITICAL: Fore.RED,
        logging.ERROR: Fore.RED,
        logging.INFO: Fore.BLUE,
        logging.WARN: Fore.YELLOW,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.colors.get(record.levelno, self.default)
        log_fmt = self.template.replace("$color$", color)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
