import hashlib
import json
import os
import os.path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tornado.ioloop
import tornado.web
import upyun

USERNAME = os.getenv('UPYUN_USERNAME') or 'username'
PASSWORD = os.getenv('UPYUN_PASSWORD') or 'password'


class MainHandler(tornado.web.RequestHandler):

    def post(self):
        data = json.loads(self.request.body.decode())
        if data.get('username') == USERNAME:
            data['password'] = hashlib.md5(PASSWORD.encode()).hexdigest()
            signature = upyun.make_signature(**data)
            print(signature)
            self.write(signature)
        else:
            print('Unknow username:', data.get('username'))


def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()
