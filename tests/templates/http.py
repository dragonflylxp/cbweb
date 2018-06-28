import ujson
from testsvr import HTTPTest


class HttpMain(HTTPTest):

    def test_main(self):
        response = self.fetch('/login/guest')
        self.assertEqual(response.code, 201)
        self.assertEqual(ujson.loads(response.body).get('message'), 'ok')

    def test_echo(self):
        response = self.fetch('/echo/requestid')
        self.assertEqual(response.code, 200)

    def test_echo1(self):
        response = self.fetch('/v1/echo')
        self.assertEqual(response.code, 200)

    def test_echo2(self):
        response = self.fetch('/v2/echo')
        self.assertEqual(response.code, 200)

    def test_echo3(self):
        response = self.fetch('/v3/echo')
        self.assertEqual(response.code, 200)

