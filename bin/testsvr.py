# coding: utf-8

import os
import sys
import argparse
import unittest
import warnings
import time
import getpass

os.environ['BASIC_PATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.environ['BASIC_PATH'], 'lib'))
sys.path.append(os.environ['PYENV_LIBS_ROOT'])

from collections import namedtuple
from tornado.testing import AsyncHTTPTestCase,AsyncTestCase,gen_test
from tornado.websocket import websocket_connect


import ews
import path


#region colorful
color_codes = namedtuple(
    'ColorCodes',
    """
    strong,weak,underline,negative,hidden,strikethrow,
    black,red,green,yellow,blue,purple,cyan,lightgray,
    black_bg,red_bg,green_bg,yellow_bg,blue_bg,purple_bg,cyan_bg,lightgray_bg
    """
)

color = color_codes(
    strong=lambda x: colorize(x, 1),
    weak=lambda x: colorize(x, 2),
    underline=lambda x: colorize(x, 4),
    negative=lambda x: colorize(x, 7),
    hidden=lambda x: colorize(x, 8),
    strikethrow=lambda x: colorize(x, 9),

    black=lambda x: colorize(x, 30),
    red=lambda x: colorize(x, 31),
    green=lambda x: colorize(x, 32),
    yellow=lambda x: colorize(x, 33),
    blue=lambda x: colorize(x, 34),
    purple=lambda x: colorize(x, 35),
    cyan=lambda x: colorize(x, 36),
    lightgray=lambda x: colorize(x, 37),

    black_bg=lambda x: colorize(x, 40),
    red_bg=lambda x: colorize(x, 41),
    green_bg=lambda x: colorize(x, 42),
    yellow_bg=lambda x: colorize(x, 43),
    blue_bg=lambda x: colorize(x, 44),
    purple_bg=lambda x: colorize(x, 45),
    cyan_bg=lambda x: colorize(x, 46),
    lightgray_bg=lambda x: colorize(x, 47)
)

def colorize(text, code):
    return '\033[{0}m{1}\033[0m'.format(code, text)

class _ColorWritelnDecorator(object):
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self,stream):
        self.stream = stream

    def __getattr__(self, attr):
        if attr in ('stream', '__getstate__'):
            raise AttributeError(attr)
        return getattr(self.stream,attr)

    def writeln(self, arg=None):
        if arg:
            self.write(arg)
        self.write('\n') # text-mode streams translate to \r\n if needed

class ColorTestResult(unittest.TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by TextTestRunner.
    """
    separator1 = '=' * 70
    separator2 = color.lightgray('-' * 70)

    def __init__(self, stream, descriptions, verbosity):
        super(ColorTestResult, self).__init__(stream, descriptions, verbosity)
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions

    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            return '\n'.join((str(test), doc_first_line))
        else:
            return str(test)

    def startTest(self, test):
        super(ColorTestResult, self).startTest(test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")
            self.stream.flush()

    def addSuccess(self, test):
        super(ColorTestResult, self).addSuccess(test)
        if self.showAll:
            self.stream.writeln("ok")
        elif self.dots:
            self.stream.write(color.green('.'))
            self.stream.flush()

    def addError(self, test, err):
        super(ColorTestResult, self).addError(test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
        elif self.dots:
            self.stream.write(color.red('E'))
            self.stream.flush()

    def addFailure(self, test, err):
        super(ColorTestResult, self).addFailure(test, err)

        if self.showAll:
            self.stream.writeln(color.yellow_bg('FAIL'))
        elif self.dots:
            self.stream.write(color.yellow('F'))
            self.stream.flush()

    def addSkip(self, test, reason):
        super(ColorTestResult, self).addSkip(test, reason)
        if self.showAll:
            self.stream.writeln("skipped {0!r}".format(reason))
        elif self.dots:
            self.stream.write("s")
            self.stream.flush()

    def addExpectedFailure(self, test, err):
        super(ColorTestResult, self).addExpectedFailure(test, err)
        if self.showAll:
            self.stream.writeln("expected failure")
        elif self.dots:
            self.stream.write("x")
            self.stream.flush()

    def addUnexpectedSuccess(self, test):
        super(ColorTestResult, self).addUnexpectedSuccess(test)
        if self.showAll:
            self.stream.writeln("unexpected success")
        elif self.dots:
            self.stream.write("u")
            self.stream.flush()

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (color.red_bg(flavour),color.yellow_bg(self.getDescription(test))))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % err)

class ColorTestRunner(object):
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    resultclass = ColorTestResult

    def __init__(self, stream=None, descriptions=True, verbosity=1,
                 failfast=False, buffer=False, resultclass=None, warnings=None,
                 *, tb_locals=False):
        """Construct a TextTestRunner.

        Subclasses should accept **kwargs to ensure compatibility as the
        interface changes.
        """
        if stream is None:
            stream = sys.stderr
        self.stream = _ColorWritelnDecorator(stream)
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        self.tb_locals = tb_locals
        self.warnings = warnings
        if resultclass is not None:
            self.resultclass = resultclass

    def _makeResult(self):
        return self.resultclass(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        unittest.registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals
        with warnings.catch_warnings():
            if self.warnings:
                # if self.warnings is set, use it to filter all the warnings
                warnings.simplefilter(self.warnings)
                # if the filter is 'default' or 'always', special-case the
                # warnings from the deprecated unittest methods to show them
                # no more than once per module, because they can be fairly
                # noisy.  The -Wd and -Wa flags can be used to bypass this
                # only when self.warnings is None.
                if self.warnings in ['default', 'always']:
                    warnings.filterwarnings('module',
                            category=DeprecationWarning,
                            message=r'Please use assert\w+ instead.')
            startTime = time.time()
            startTestRun = getattr(result, 'startTestRun', None)
            if startTestRun is not None:
                startTestRun()
            try:
                test(result)
            finally:
                stopTestRun = getattr(result, 'stopTestRun', None)
                if stopTestRun is not None:
                    stopTestRun()
            stopTime = time.time()
        timeTaken = stopTime - startTime
        result.printErrors()
        if hasattr(result, 'separator2'):
            self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %s test%s in %s" %
                            (color.green_bg(str(run)), color.cyan_bg(run != 1 and "s" or ""), color.cyan_bg
                            ("%0.3f" % timeTaken)))
        self.stream.writeln()

        expectedFails = unexpectedSuccesses = skipped = 0
        try:
            results = map(len, (result.expectedFailures,
                                result.unexpectedSuccesses,
                                result.skipped))
        except AttributeError:
            pass
        else:
            expectedFails, unexpectedSuccesses, skipped = results

        infos = []
        if not result.wasSuccessful():
            self.stream.write("FAILED")
            failed, errored = len(result.failures), len(result.errors)
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            self.stream.write(color.underline(color.strikethrow('OK')))
        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        if infos:
            self.stream.writeln(" (%s)" % (", ".join(infos),))
        else:
            self.stream.write("\n")
        return result
#endregion


class HTTPTest(AsyncHTTPTestCase):

    def setUp(self):
        super(HTTPTest, self).setUp()
        self.host = os.environ['unittest_http_host']

    def get_app(self):
        return ews.get_application()

    def get_new_ioloop(self):
        return ews.current_ioloop()

    def get_http_port(self):
        return os.environ['unittest_http_port']

    def get_url(self, path):
        return '%s://%s:%s%s' % (self.get_protocol(), self.host, self.get_http_port(), path)

class UnitTestTool(object):
    def __init__(self, args):
        self.suite = unittest.TestSuite()
        self.loader = unittest.TestLoader()
        self.args = args

        sys.path.append(path._TEST_PATH)
        os.environ['unittest_http_host'] = self.args.h
        os.environ['unittest_http_port'] = self.args.p

    def run(self):
        if self.args.m == 'all':
            self.load_all_test()
        else:
            self.load_test()

        if self.args.v:
            self.html_render()
        else:
            self.console_render()

    def load_all_test(self):
        modules = [__import__(sub_dir) for sub_dir in os.listdir(path._TEST_PATH)
                   if sub_dir not in ['__pycache__','templates','logs']]
        for module in modules:
            load_modules = [module.__name__ + '.' + sub_module for sub_module in module.__all__]
            tests = self.loader.loadTestsFromNames(load_modules)
            self.suite.addTests(tests)

    def load_test(self):
        module = __import__(args.m, fromlist=['*'])
        tests = self.loader.loadTestsFromModule(module)
        self.suite.addTests(tests)

    def console_render(self):
        runner = ColorTestRunner()
        runner.resultclass = ColorTestResult
        runner.run(self.suite)

    def html_render(self):
        try:
            HTMLTestRunner = __import__('HTMLTestRunner')
            # TBD 输出测试记录，需要安装外部包HTMLTestRunner
            with open('logs/%s-%s.html' % (getpass.getuser(),time.strftime('%Y-%m-%d %H:%M:%S'))) as fp:
                runner = HTMLTestRunner(stream=fp,title=u'XXXX接口测试用例',description=u'接口列表：')
                runner.run(self.suite)
        except ModuleNotFoundError as e:
            print(e.msg)
            print('导出日志需要额外导入HTMLTestRunner文件，当前使用终端输出')
            print(color.red_bg('*' * 70))
            self.console_render()


if __name__ == '__main__':
    # 在项目跟目录下进入bin目录，支持如下命令

    # `python testsvr.py` ，该命令会启动测试模块中所有的测试案例
    # `python testsvr.py --m 模块名.文件名` ， 可以启动对指定文件的测试案例
    # `python testsvr --h 主机名 --p 端口 -m 模块名`
    parser = argparse.ArgumentParser('EWS cmd options:')
    parser.add_argument('--h', default='localhost', help="--h localhost ******测试主机")
    parser.add_argument('--p', default='8000', help="--p 8000 ******测试端口")
    parser.add_argument('--m', default='all', help="--m 模块名.类名 ******指定模块")
    parser.add_argument('--v', action='store_true', help="--v ******是否输出测试结果文档")
    args = parser.parse_args()

    UnitTestTool(args).run()
