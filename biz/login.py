# coding: utf-8

import time
import uuid

import ews


@ews.route_sync_func('/login/guest') # 如果内容含有阻塞的调用，需要使用这种装饰器
def login_guest(handler, *args, **kwargs):
    time.sleep(0.1)
    return handler.ok({'sessionid': str(uuid.uuid1())})

@ews.route_sync_func('/echo/requestid')
def login_guest(handler, *args, **kwargs):
    return handler.ok({'sessionid': str(uuid.uuid1())})

