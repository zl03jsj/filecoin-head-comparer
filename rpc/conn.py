import json
import requests


class _conn:
    def __init__(self, name, url, token):
        self.name = name
        self.url = url
        self.header = None

        if token and len(token) != 0:
            self.header = {'Authorization': 'Bearer ' + token,
                           'Content-Type': 'application/json'}

        self.payload = {"jsonrpc": "2.0", "id": 1, }

    def parse_result(self, res):
        cids = [x['/'] for x in ((res['Cids'] if 'Cids' in res else res['Key']))]
        b = res['Blocks'][0]
        return {'cids': cids, 'height': b["Height"] if "Height" in b else b['height'],
                'name': self.name}

    def post(self, method, params):
        if not isinstance(method, str):
            raise ValueError('method required to be string')
        self.payload["method"] = method

        if params and not isinstance(params, list):
            raise ValueError('params required to be list')
        self.payload["params"] = []

        res = requests.request("POST", self.url, headers=self.header,
                               data=json.dumps(self.payload))
        if res.status_code != 200:
            print("unexpected, post to %s failed, status_code=%d" % (self.name, res.status_code))
            return
        return self.parse_result(json.loads(res.text)["result"])


class _conns:
    conns = []

    def __init__(self, conns=None):
        if not conns:
            return

        if not isinstance(conns, list):
            raise ValueError('conns required to be list[conn]')

        for c in conns:
            if not isinstance(c, _conn):
                raise ValueError('conns required to be list[conn]')
            self.conns.append(c)

    def insert(self, c):
        if not isinstance(c, _conn):
            raise ValueError('conns required to be list[conn]')
        self.conns.append(c)

    def post(self, method, params=None):
        ress = []
        for idx, val in enumerate(self.conns):
            res = val.post(method, params)
            if res != None:
                ress.append(res)
        return ress

    def do_check_heads(self):
        res = self.post("Filecoin.ChainHead")

        matchs = True
        d_0 = json.dumps((res[0]['height'], res[0]['cids']))

        for idx in range(1, len(res)):
            d = json.dumps((res[idx]['height'], res[idx]['cids']))
            if d_0 != d:
                matchs = False
                break

        if matchs:
            print('expected, height : %d, 100%%-match\n' % (res[0]['height']))
            return

        print('unexpected, height: %d mis-match' % (res[0]['height'],))
        for idx, val in enumerate(res):
            print("|----%s--------\n|-chain_head: height:%d\n|-blocks:%s" % (
                val['name'], val['height'], val['cids']))
        print('|-------------------------------------------------------------\n')
