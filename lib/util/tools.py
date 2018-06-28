#coding=utf-8
import base64
import hashlib
import inspect
import logging
import logging.config
import os
import threading
import traceback
import uuid
import xml.sax
import xml.sax.handler

import curl
import ujson as ujson
import util.xml_util
import requests
import time
import sys
import path
import ews
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5 as pk

#reload(sys)
#sys.setdefaultencoding('utf-8')

class Log():
    logger = None

    @classmethod
    def set_up(cls, log_cnf):
        logging.config.fileConfig(log_cnf['config_file'])
        Log.logger = logging.getLogger(log_cnf['default_logger'])

    def getLog(self):
        if Log.logger == None:
            Log.logger = logging.getLogger('simple')
        return Log.logger


class XMLHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.buffer = ""
        self.mapping = {}

    def startElement(self, name, attributes):
        self.buffer = ""

    def characters(self, data):
        self.buffer += data

    def endElement(self, name):
        self.mapping[name] = self.buffer

    def getDict(self):
        return self.mapping



class RequestXml:
    @ staticmethod
    def http_request_get(url, params=None, timeout=8):
        try:
            t1 = time.time()
            xml = requests.get(str(url), params)
            t2 = time.time()
            Log().getLog().info("url=%s|spendTime=%s", url, (t2 - t1))
            return xml
        except:
            Log().getLog().exception("==== url[%s] ====", url)
            raise
        finally:
            pass

    @staticmethod
    def get_xml_dom(url, params=None, timeout=8):
        try:
            url = url.encode("utf-8")
        except Exception as ex:
            url = str(url)
            Log().getLog().error(ex)

        xml = RequestXml.http_request_get(url, params=params, timeout=timeout)
        try:
            #Log().getLog().debug(xml.text)
            dom = xml_util.parse_xml(xml.text)

        except Exception as e:
            Log().getLog().info((url, e))
            raise e
        return dom

class Profiler:
    clicks = {}

    @staticmethod
    def time_cost(func):
        def wrapper(*args, **kwargs):
            tid = threading.current_thread().ident
            key = str(tid)+func.__name__
            ret = func(*args, **kwargs)
            Log().getLog().debug("Profiler Time cost: func_name=%s|ret=%s",func.__name__,['t{}-t{}={}'.format(idx+1,idx,Profiler.clicks[key][idx]-Profiler.clicks[key][idx-1]) for idx,k in enumerate(Profiler.clicks[key]) if idx>0])
            Profiler.clicks[key] = []
            return ret
        return wrapper

    @staticmethod
    def click(fname):
        tid = threading.current_thread().ident
        key = str(tid)+fname
        if Profiler.clicks.has_key(key):
            Profiler.clicks[key].append(time.time())
        else:
            Profiler.clicks[key] = [time.time()]


    @staticmethod
    def curfunc_name():
        return inspect.stack()[1][3]


class CurlHttpRequest(object):
    '''发送http相关请求
    '''

    @staticmethod
    def post(url, timeout=8, params={}):
        cc = None
        try:
            t1 = time.time()
            cc = curl.Curl()
            cc.set_timeout(timeout)
            resp = cc.post(str(url), params)
            t2 = time.time()
            t = t2 - t1
            Log.logger.info("curlHttpPost|url=%s|params=%s|resp=%s|spendTime=%f", url, params, resp, t)
            return resp
        except:
            Log.logger.error("curl tcm api interface error %s |params %s", url, params)
            Log.logger.error(traceback.format_exc())
            raise ews.EwsError(ews.STATUS_REQUEST_TIMEOUT)
        finally:
            if cc:
                cc.close()

    @staticmethod
    def get(url, timeout=8, params=None, return_codeing="utf8"):
        '''
            注意,如果返回的报文内容较大, 请勿使用, 因为日志打印了resp
            @params: timeout 超时时间
            @params: params 请求参数
        '''
        try:
            t1 = time.time()
            cc = curl.Curl()
            cc.set_timeout(timeout)
            resp = cc.get(str(url), params)
            if return_codeing != "utf8":
                resp = resp.decode(return_codeing)

            if not params:
                params = {}

            t2 = time.time()
            Log.logger.info("curlHttpRequest|url=%s|timeout=%s|params=%s|resp=%s|spendtime=%f", url, timeout, urllib.urlencode(params), resp[:200], (t2 - t1))
            return resp
        except:
            Log.logger.error("curl tcm api interface error %s |params %s", url, params)
            Log.logger.error(traceback.format_exc())
            raise ews.EwsError(ews.STATUS_REQUEST_TIMEOUT)
        finally:
            cc.close()


class TCMRequest:
    PRIVATEKEY = path._DAT_PATH + '/rsa_private_key.pem'
    common_params = {'vendorId': '500', 'appId': '500-001'}

    @staticmethod
    def pack(params):
        # 打包TCM请求参数
        params = {'businessParam': ujson.dumps(params)}
        params['requestId'] = str(uuid.uuid1())
        params['timestamp'] = int(time.time())
        params.update(TCMRequest.common_params)
        try:
            with open(TCMRequest.PRIVATEKEY) as fd:
                prikey = RSA.importKey(fd.read())
            sign = TCMRequest.get_sign(params, "RSA", prikey)
            params['sign'] = sign.decode()
        except:
            print(traceback.format_exc())
            return {}
        return params

    @staticmethod
    def alphabet_sort(params):
        # 剔除sign并按字母排序
        target = []
        for k, v in params.items():
            if k != 'sign': target.append('{}={}'.format(str(k), str(v)))
        target.sort()
        return '&'.join(target)

    @staticmethod
    def get_sign(params, htype, prikey):
        # MD5或RSA生成sign
        target = TCMRequest.alphabet_sort(params)
        if htype == 'MD5':
            m = hashlib.md5()
            m.update(target + prikey)
            return m.hexdigest()
        elif htype == 'RSA':
            hasher = SHA.new(target.encode())  # 默认是SHA-1
            signer = pk.new(prikey)
            return base64.b64encode(signer.sign(hasher))
        else:
            return ""

    @staticmethod
    def verify_sign(params, sign, htype, pubkey):
        # MD5或者RSA验证sign
        target = TCMRequest.alphabet_sort(params)
        if htype == 'MD5':
            m = hashlib.md5()
            m.update(target + pubkey)
            return m.hexdigest() == sign
        elif htype == 'RSA':
            hasher = SHA.new(target)
            sign = base64.b64decode(sign)
            verifier = pk.new(pubkey)
            return verifier.verify(hasher, sign)
        else:
            return False
