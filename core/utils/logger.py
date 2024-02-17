import sys
import re

from loguru import logger


def logging_setup():
    format_info = "<green>{time:HH:mm:ss.SS}</green> <blue>{level}</blue> <level>{message}</level>"
    format_error = "<green>{time:HH:mm:ss.SS}</green> <blue>{level}</blue> | " \
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
    file_path = r"logs/"

    logger.remove()

    logger.add(file_path + "out.log", colorize=True,
               format=clean_brackets(format_error))

    logger.add(sys.stdout, colorize=True,
               format=format_info, level="INFO")  # , level="INFO"
    # logger.add(sys.stderr, level=log_level, format=log_format, colorize=True, backtrace=True, diagnose=True)


def clean_brackets(raw_str):
    clean_text = re.sub(brackets_regex, '', raw_str)
    return clean_text


brackets_regex = re.compile(r'<.*?>')

logging_setup()
