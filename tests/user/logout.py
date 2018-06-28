from testsvr import HTTPTest

class EchoMain(HTTPTest):
    def test_main(self):
        response = self.fetch('/echo/requestid')
        # print(response.body)
        self.assertEqual(response.code, 200)