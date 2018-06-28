# coding: utf-8

import ujson
import traceback
from tornado.websocket import WebSocketHandler
import tornado.ioloop
import ews
from util.tools import Log
logger = Log().getLog()

@ews.route_handler_class('/crazybet')
class CrazybetWebsockHandler(WebSocketHandler):

    def prepare(self):
        pass

    def check_origin(self, origin):
        return True

    def open(self):
        logger.debug('A client has connected! HandlerID=%s', id(self))

    def on_message(self, msg):
        if msg == 'x':  #ping
            self.write_message('you said:%s' % msg)
        else:
            logger.debug('HandlerID=%s|ReceivedMsg=%s', id(self), msg)

    def on_close(self):
        logger.debug('Websocket closed! HandlerID=%s', id(self))
        self.close()

    def write_message(self,msg):
        if not self.stream.closed():
            super(CrazybetWebsockHandler,self).write_message(msg)
        else:
            self.on_connection_close()
