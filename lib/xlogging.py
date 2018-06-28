# coding: utf-8
"""Easy Logging
@version: 0.1
"""

import logging
import logging.config


def set_default_logger(logger_name=None):
    """设置默认的logger
    """
    global dft_logger, debug, info, warning, error, critical, exception
    if logger_name is None:
        dft_logger = logging.getLogger() # get root logger
        debug = logging.debug
        info = logging.info
        warning = logging.warning
        error = logging.error
        critical = logging.critical
        exception = logging.exception
    else:
        dft_logger = logging.getLogger(logger_name)
        debug = dft_logger.debug
        info = dft_logger.info
        warning = dft_logger.warning
        error = dft_logger.error
        critical = dft_logger.critical
        exception = dft_logger.exception
set_default_logger() # set the root logger as the default logger


def get_default_logger():
    global dft_logger
    return dft_logger


def basic_config(config):
    logging.basicConfig(config)


def dict_config(config):
    logging.config.dictConfig(config)


def ini_config(fname):
    logging.config.fileConfig(fname)

