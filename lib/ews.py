# coding: utf-8
"""Esun Web Service
@version: 0.3
@todo: 解决非ThreadFuncHandler的prepare_json_args等问题
使用例子：
    import time
    import ews
    @ews.route_sync_func('/a')
    def aa(handler, *args, **kwargs):
        time.sleep(1)
        return 'hello'
    class bbbb(object):
        @ews.route_sync_func('/b', kwargs={ # 可以在这里登记参数和默认值，也为以后的文档自动化做准备
            'k1': ('v1', '这个地方是参数说明和注释'),
            'k2': (UserWarning, '这里表示没有默认参数，调用方必须传值'),
        })
        def bb(self, handler, *args, **kwargs):
            return handler.ok({'asdf': 'qwer'})
    @ews.route_handler_class('/c')
    class cccc(tornado.web.RequestHandler):
        def get(self, *args, **kwargs):
            self.write('world')
    ews.listen(8888)
    ews.start()
"""

import os
import sys
import atexit
import signal
import functools
import inspect
import imp
import copy
import glob

import ujson
import tornado.ioloop
from tornado.log import access_log, app_log

import xtornado




STATUS_OK = '100'
STATUS_BUSY = '99'
STATUS_PARAM = '96'
STATUS_ERROR = '101'
status_msgs = {
    STATUS_OK : 'ok',
    STATUS_BUSY : '系统超负荷啦，攻城狮正忙着调资源，您先歇一会再试试啦~',
    STATUS_PARAM : 'bad or lack parameter',
    STATUS_ERROR : '哦噢，系统开小差了，攻城狮正在修复中，您先歇一会再试试啦~',
}
def get_status_msg(st_code):
    return status_msgs.get(st_code) or \
            '火星报文[%s]。如果您看到了这个，请帮忙截屏给我们客服看看，谢谢！' % st_code


class EwsError(Exception):
    """自定义一个错误类，在业务代码里面raise这个类可以触发write_error输出统一格式的错误报文。"""
    pass




class ThreadFuncHandler(xtornado.ThreadFuncHandler):
    """for synchronize function call
    @todo: overwrite "log_exception"
    """

    def options(self, *args, **kwargs):
        # 允许跨域请求
        self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Accept, Cache-Control, Content-Type")

    def ok(self, data, extd=None):
        """组织处理成功的返回报文内容
        """
        ret = {
            'status': STATUS_OK,
            'message': get_status_msg(STATUS_OK),
            'data': data,
        }
        if extd:
            ret['extd'] = extd
        ret = ujson.dumps(ret, ensure_ascii=False)
        if self.json_args.get('js_callback'):
            self.set_header('Content-Type', 'application/javascript; charset=UTF-8')
            return '%s(%s)' % (self.json_args['js_callback'], ret)
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            return ret

    def write_error(self, status_code=500, **kwargs):
        """覆盖原tornado的write_error，输出统一格式的错误报文。"""
        if status_code == 500:
            if "exc_info" in kwargs and isinstance(kwargs['exc_info'][1], EwsError):
                ex = kwargs['exc_info'][1]
                ret = {
                    'status': ex.args[0],
                    'message': get_status_msg(ex.args[0]),
                    'data': {},
                }
                if len(ex.args) > 1:
                    ret['message'] = ex.args[1] # 异常里面指定了给用户的反馈语
            else:
                ret = {
                    'status': STATUS_ERROR,
                    'message': get_status_msg(STATUS_ERROR),
                    'data': {},
                }
        else:
            ret = {
                'status': str(status_code),
                'message': get_status_msg(status_code),
                'data': {},
            }
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.finish(ujson.dumps(ret, ensure_ascii=False))


@ThreadFuncHandler.prepare_plugin()
def allow_cross_site(handler):
    # 允许跨域请求
    req_origin = handler.request.headers.get("Origin")
    if req_origin:
        handler.set_header("Access-Control-Allow-Origin", req_origin)
        handler.set_header("Access-Control-Allow-Credentials", "true")
        handler.set_header("Allow", "GET, HEAD, POST")


@ThreadFuncHandler.prepare_plugin()
def prepare_json_args(handler):
    """分析请求参数
    """
    # 初始化默认参数
    json_args = dict((k, v[0]) for k, v in route_entries.get(handler.route_path)['kwargs'].items())
    # 处理用户输入的参数
    if handler.request.headers.get('Content-Type', '').find("application/json") >= 0:
        # json格式请求
        try:
            user_args = ujson.loads(handler.request.body)
        except Exception as ex:
            handler.write_error(STATUS_PARAM)
            return
    else:
        # 普通参数请求
        user_args = dict((k, v[-1]) for k, v in handler.request.arguments.items())
    # 参数检查
    json_args.update(user_args)
    for k, v in json_args.items():
        if v == UserWarning:
            # 有必填参数未传值
            handler.write_error(STATUS_PARAM)
            return
    handler.json_args = json_args




############################################################




route_handler_class = xtornado.route_handler_class
listen = xtornado.listen
stop = xtornado.stop
get_application = xtornado.get_application
add_handler = xtornado.add_handler
current_ioloop = xtornado.current_ioloop


route_entries = {}
def route_sync_func(route_path, handler_class=ThreadFuncHandler, kwargs={}):
    """扩展xtornado的route_sync_func，支持对class的method做修饰。
    由于被修饰的class在修饰method在这里还没处于可用状态，要到start的时候才延时载入
    """
    if route_path[0] != '/':
        route_path = '/' + route_path
    def deco_func(exec_func):
        route_entries[route_path] = {
            'route_path': route_path,
            'class_name': inspect.stack()[1][3],
            'exec_func': exec_func,
            'handler_class': handler_class,
            'doc': exec_func.__doc__,
            'kwargs': kwargs,
        }
        return exec_func # 做好登记就可以了，不需要修饰原来的函数功能
    return deco_func


def load_biz_dir(dir_path):
    """载入biz_dir目录里面的所有py文件，主要是为了方便route_sync_func等业务自动注册
    """
    for fname in os.listdir(dir_path):
        # if fname[0] in '._':
        #     continue
        if fname[-3:] != '.py':
            continue
        fpath = os.path.join(dir_path, fname)
        if not os.path.isfile(fpath):
            continue
        imp.load_source('_biz_' + fname[:-3], fpath)


stop_plugins = []
def add_stop_plugin(func, *args, **kwargs):
    stop_plugins.append([func, args, kwargs])
# 注册SIGTERM信号处理
signal.signal(signal.SIGTERM, lambda signum, frame: xtornado.stop())


def start():
    # 登记xtornado路由
    def local_func(exec_func, route_path, handler_class):
        @xtornado.route_sync_func(route_path, handler_class)
        def deco_func(*args, **kwargs):
            return exec_func(*args, **kwargs)
    for route_info in route_entries.values():
        if route_info['class_name'] == '<module>':
            exec_func = route_info['exec_func']
        else:
            # 给method做修饰的时候，method所属的class还没处于可用状态，延迟到这里才生成对象
            cls = getattr(sys.modules[route_info['exec_func'].__module__], route_info['class_name'])
            exec_func = getattr(cls(), route_info['exec_func'].__name__)
        # 录入到xtornado
        local_func(exec_func, route_info['route_path'], route_info['handler_class'])
    # todo: 远程注册服务，定时心跳通知
    # 开始服务
    get_application().settings['log_function'] = log_function
    xtornado.start()
    # 调用停止服务需要执行的插件
    for plg in stop_plugins:
        try:
            plg[0](*plg[1], **plg[2])
        except Exception as ex:
            app_log.exception('something wrong when stopping: {0}'.format(plg[0]))


def log_function(handler):
    """记录请求日志
    """
    if handler.get_status() < 400:
        log_method = access_log.info
    elif handler.get_status() < 500:
        log_method = access_log.warning
    else:
        log_method = access_log.error
    req = handler.request
    log_method('%s "%s" %d %s %.6f',
               req.method, req.uri, handler.get_status(),
               req.remote_ip, req.request_time() )
