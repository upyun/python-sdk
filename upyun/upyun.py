# -*- coding: utf-8 -*-
import hashlib
import os

from .rest import UpYunRest
from .form import FormUpload
from .av import AvPretreatment

from .modules.httpipe import UpYunHttp
from .modules.exception import UpYunClientException
from .modules.compat import b
from .modules.sign import make_signature

ED_LIST = ('v%d.api.upyun.com' % ed for ed in range(4))
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST

DEFAULT_CHUNKSIZE = 8192


class UpYun(object):
    def __init__(self, bucket, username=None, password=None,
                 auth_server=None, timeout=None, endpoint=None,
                 chunksize=None, debug=False, read_timeout=None):
        super(UpYun, self).__init__()
        self.bucket = bucket or os.getenv('UPYUN_BUCKET')
        self.username = username or os.getenv('UPYUN_USERNAME')
        password = password or os.getenv('UPYUN_PASSWORD')
        self.password = (hashlib.md5(b(password)).hexdigest()
                         if password else None)
        self.auth_server = auth_server
        self.endpoint = endpoint or ED_AUTO
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.timeout = timeout or 60
        if read_timeout is not None:
            self.requests_timeout = (self.timeout, read_timeout)
        else:
            self.requests_timeout = self.timeout
        self.hp = UpYunHttp(self.requests_timeout, debug)

        self.up_rest = UpYunRest(self.bucket, self.username, self.password,
                                 self.auth_server, self.endpoint,
                                 self.chunksize, self.hp)
        self.av = AvPretreatment(self.bucket, self.username, self.password,
                                 self.auth_server, self.chunksize, self.hp)
        self.up_form = FormUpload(self.bucket, self.username, self.password,
                                  self.auth_server, self.endpoint, self.hp)

        if debug:
            self.__init_debug_log(bucket=bucket, username=username,
                                  password=password, auth_server=auth_server,
                                  timeout=timeout, endpoint=endpoint,
                                  chunksize=chunksize, debug=debug)

    def __init_debug_log(self, **kwargs):
        with open('debug.log', 'w') as f:
            f.write('### Running in debug mode ###\n\n\n')
            f.write('## Initial params ##\n\n')
            f.write('\n'.join(
                map(lambda kv: '%s: %s' % (kv[0], kv[1]), kwargs.items())))

    def set_endpoint(self, endpoint, host=None):
        self.up_rest.endpoint = endpoint
        self.up_rest.host = host or ED_AUTO

    def verify_signature(self, signature, uri, headers):
        data = {
            'username': self.username,
            'password': self.password,
            'method': 'POST',
            'uri': uri,
            'date': headers['Date'],
            'auth_server': self.auth_server
        }
        if 'Content-MD5' in headers:
            data['content_md5'] = headers['Content-MD5']
        return signature == make_signature(**data)

    # --- public rest API
    def usage(self, key='/'):
        return self.up_rest.usage(key)

    def put(self, key, value, checksum=False, headers=None,
            handler=None, params=None, secret=None,
            need_resume=False, store=None, reporter=None,
            form=False, expiration=None, **kwargs):
        if form and hasattr(value, 'fileno'):
            return self.up_form.upload(key, value, expiration, **kwargs)
        return self.up_rest.put(key, value, checksum, headers, handler, params,
                                secret, need_resume, store, reporter)

    def get(self, key, value=None, handler=None, params=None):
        return self.up_rest.get(key, value, handler, params)

    def delete(self, key):
        self.up_rest.delete(key)

    def mkdir(self, key):
        self.up_rest.mkdir(key)

    def getlist(self, key='/', limit=None, order=None,
                begin=None):
        return self.up_rest.getlist(key, limit, order, begin)

    def iterlist(self, key='/', limit=None, order=None,
                 begin=None):
        return self.up_rest.iterlist(key, limit, order, begin)

    def getinfo(self, key):
        return self.up_rest.getinfo(key)

    def purge(self, keys, domain=None):
        return self.up_rest.purge(keys, domain)

    # --- video pretreatment API
    def pretreat(self, tasks, source, notify_url=''):
        return self.av.pretreat(tasks, source, notify_url)

    def status(self, taskids):
        return self.av.status(taskids)

    # --- depress task
    def depress(self, tasks, notify_url):
        for task in tasks:
            save_as = task.get('save_as')
            sources = task.get('sources')
            for key in (sources, save_as):
                if not isinstance(key, str) or key == '':
                    raise UpYunClientException('Given not correct %s '
                                               'in task' % key)
        return self.av.pretreat(tasks, 'upyun', notify_url, 'depress')

    # --- compress task
    def compress(self, tasks, notify_url):
        for task in tasks:
            save_as = task.get('save_as')
            sources = task.get('sources')
            if not isinstance(save_as, str) or save_as == '':
                raise UpYunClientException('Given not correct save_as in task')
            if not isinstance(sources, list) or len(sources) == 0:
                raise UpYunClientException('Given not correct sources in task')
        return self.av.pretreat(tasks, 'upyun', notify_url, 'compress')

    def put_tasks(self, tasks, notify_url, app_name):
        return self.av.pretreat(tasks, '', notify_url, app_name)


    def update_cache(self, urls):
        """
        >>>    url1 = "http://test.b0.upaiyun.com/user_001.flv"
        >>>    url2 = "http://test.b0.upaiyun.com/user_002.flv"
        >>>    urls = [url1, url2]
        >>>    res = up.update_cache(urls)
        >>>    return tuple (status, content)
        """

        purge_host = "purge.upyun.com"
        # Date Format: RFC 1123
        dt = httpdate_rfc1123(datetime.datetime.utcnow())

        # 每个url之间用"\n"分割，并且每个url都必须以为http开头，否则不会加入刷新队列，
        # 刷新的url数量每分钟有600个限制，且每次最多不超过50个。
        # url = "文件url的完整路径1\n文件url的完整路径2\n"
        purge_str = "\n".join(urls)

        # sign = md5(url + "&" + bucket + "&" + date + "&" + token);
        signature = hashlib.md5("&".join([purge_str, self.bucket, dt, self.password])).hexdigest()
        authorization = 'UpYun ' + self.bucket + ":" + self.username + ":" + signature
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Date": dt,
            "Authorization": authorization
        }

        body = {"purge": purge_str}
        body = urllib.urlencode(body)

        content, msg, err, status = None, None, None, None
        if HTTP_EXTEND is True:
            URL = "http://" + purge_host + "/purge/"
            requests.adapters.DEFAULT_RETRIES = 5
            try:
                response = self.session.request("POST", URL, data=body,
                                                headers=headers,
                                                timeout=self.timeout)
                content = (response.status_code, response.content)
            except requests.exceptions.ConnectionError as e:
                raise UpYunClientException(str(e))
            except requests.exceptions.RequestException as e:
                raise UpYunClientException(str(e))
            except Exception as e:
                raise UpYunClientException(str(e))
        else:
            try:
                connection = httplib.HTTPConnection(purge_host, timeout=self.timeout)
                # connection.set_debuglevel(1)
                connection.request("POST", "/purge/", body, headers)
                response = connection.getresponse()
                content = (response.status, response.read())
            except (httplib.HTTPException, socket.error, socket.timeout) as e:
                raise UpYunClientException(str(e))
            except Exception as e:
                raise UpYunClientException(str(e))
            finally:
                if connection:
                    connection.close()

        return content

if __name__ == '__main__':
    pass
