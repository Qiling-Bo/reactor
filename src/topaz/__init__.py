#!/usr/bin/env python
# encoding: utf-8
"""AgigaTech project "topaz" PGEM burnin program.
"""

__version__ = 0.3
__author__ = "@boqiling"

import logging
import os
import sys
from color import ColorizingStreamHandler


def init_log(LOG_FILE):
    if os.path.isfile(LOG_FILE):
        os.remove(LOG_FILE)     # remove the log file

    logger = logging.getLogger()
    formatter = logging.Formatter('[ %(asctime)s ] %(levelname)s %(message)s')

    # add stdout handler
    # stdhl = logging.StreamHandler(sys.stdout)
    stdhl = ColorizingStreamHandler(sys.stdout)
    stdhl.setFormatter(formatter)
    stdhl.setLevel(logging.DEBUG)   # print everything

    # add file handler
    hdlr = logging.FileHandler(LOG_FILE)
    hdlr.setFormatter(formatter)
    hdlr.setLevel(logging.WARNING)   # save WARNING, EEROR and CRITICAL to file

    logger.addHandler(hdlr)
    logger.addHandler(stdhl)
    logger.setLevel(logging.DEBUG)
    return logger

log = "error.log"
logger = init_log(log)
