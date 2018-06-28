#!/usr/bin/env python
# encoding: utf-8
import ujson
import job
import xmsgbus
from util.tools import Log
logger = Log().getLog()

@job.scheduler.scheduled_job('cron',second='*/10')
def demo_job():
    logger.info('demo job')
    xmsgbus.send(queue='test', msg='test send')
