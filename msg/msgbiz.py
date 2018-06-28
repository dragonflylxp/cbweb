#!/usr/bin/env python
# encoding: utf-8
import sys
import ujson
import traceback
import xmsgbus
from util.tools import Log
logger = Log().getLog()

@xmsgbus.subscribe_callback_register("HelloWorld")
def hello_world(channel, msg):
    msg = ujson.loads(msg)
    logger.debug(msg)
