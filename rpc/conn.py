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

    def parse_head(self, res):
        # [x['/'] for x in ((res['Cids'] if 'Cids' in res else res['Key']))]
        cids = res['Key'] if 'Key' in res else (res['Cids'] if 'Cids' in res else None)
        blks = res['Blocks'][0]
        return {'cids': cids, 'blocks': res['Blocks'],
                'height': blks["Height"] if "Height" in blks else blks['height'], 'name': self.name}

    def post(self, method, params):
        # {"id": 1, "jsonrpc": "2.0", "params": [{"offset_range": {"start": 0, "count": 25}, "method": "PreCommitSector"}],
        #  "method": "filscan.GetMessages"}
        method = method

        if not isinstance(method, str):
            raise ValueError('method required to be string')
        self.payload["method"] = method

        if params and not isinstance(params, list):
            raise ValueError('params required to be list')

        self.payload["params"] = params

        res = requests.request("POST", self.url, headers=self.header, data=json.dumps(self.payload))
        if res.status_code != 200:
            res_obj = json.loads(res.text)
            print("unexpected, post to %-15s failed, status_code=%d, error=%s" % (self.name, res.status_code, res_obj['error']))

            return
        if method == 'Filecoin.ChainHead':
            return self.parse_head(json.loads(res.text)["result"])
        else:
            json_obj = json.loads(res.text)

            if 'result' in json_obj:
                return {'name': self.name, 'result': json_obj['result']}
            else:
                print("|- method:%s returns error\n|- params:%s\n|- message:%s" % (method, params, json_obj['error']['message']))
                return {'name': self.name, 'result': json_obj['error']}


def to_josn(d, exclude=[]):
    d = d if d is None or isinstance(d, int) or isinstance(d, str) else d.copy()
    if len(exclude) > 0 and isinstance(d, dict):
        for k in exclude:
            if k in d.keys(): del d[k]
    return json.dumps(d, default=lambda o: o.__dict__, sort_keys=True).lower()


class _precommit_sector_provider:
    def __init__(self, url):
        self.url = url
        self.conn = _conn("precommitsectors_provider", self.url, "")

    def precommitsectors(self):
        res = self.conn.post("filscan.GetMessages", [{"offset_range": {"start": 0, "count": 10}, "method": "PreCommitSector"}])
        res = res['result']['data']

        if not isinstance(res, list) and not isinstance(res, slice): return None

        return [[s['to'], s['args']['SectorNumber']] for s in res]

    def precommitsectorsV2(self):
        res = requests.get('https://filfox.info/api/v1/message/list?pageSize=5&page=0&method=PreCommitSector')
        if res.status_code != 200:
            return None
        res = json.loads(res.text)
