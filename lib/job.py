# coding: utf-8

import os
import sys
from tornado.ioloop import IOLoop
from apscheduler.schedulers.tornado import TornadoScheduler
import apscheduler
#from apscheduler.schedulers.blocking import BlockingScheduler
from util.tools import Log
logger = Log().getLog()

#定时器
#scheduler = BlockingScheduler()
scheduler = TornadoScheduler()

#事件监听句柄
def job_events_listener(jobEvent):
    job = scheduler.get_job(jobEvent.job_id)
    if jobEvent.code == apscheduler.events.EVENT_JOB_EXECUTED:
        logger.info("jobname=%s|jobtrigger=%s|jobtime=%s|timecost=%s", job.name, job.trigger, jobEvent.scheduled_run_time, jobEvent.retval)
    else:
        logger.error("jobname=%s|jobtrigger=%s|errcode=%s|exception=[%s]|traceback=[%s]|scheduled_time=%s", job.name, job.trigger, jobEvent.code,
                     jobEvent.exception,jobEvent.traceback, jobEvent.scheduled_run_time)


def attach(ioloop):
    scheduler._configure({"io_loop":ioloop})
    scheduler.add_listener(job_events_listener, apscheduler.events.EVENT_JOB_ERROR | \
                        apscheduler.events.EVENT_JOB_MISSED | \
                        apscheduler.events.EVENT_JOB_EXECUTED)
    scheduler.start()
