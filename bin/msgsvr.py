# coding: utf-8

import os
import sys
import argparse

os.environ['BASIC_PATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.environ['BASIC_PATH'], 'lib'))
sys.path.append(os.environ['PYENV_LIBS_ROOT'])

import ews
import xmsgbus
import path
from util import db_pool
from util.tools import Log
from util.configer import *

def init(conf_file):
    # 载入配置文件
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    confs = JsonConfiger.get_instance()
    confs.load_file(conf_file)

    # 初始化日志
    log_cnf = confs.get('logging')
    if log_cnf['config_file'][:1] not in ['/', '\\']:
        log_cnf['config_file'] = os.path.join(os.path.dirname(os.path.abspath(conf_file)), log_cnf['config_file'])
    Log.set_up(log_cnf)
    global logger
    logger = Log().getLog()

    #加载业务代码
    ews.load_biz_dir(path._MSG_PATH)

    # 初始化消息总线
    xmsgbus.set_up(confs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser('EWS cmd options:')
    parser.add_argument('-c', default=os.path.join(path._ETC_PATH, 'includes_dev.json'), help="-c cfgfile ******加载配置文件")
    args = parser.parse_args()

    init(args.c)
    xmsgbus.attach(ews.current_ioloop())
    ews.start()
