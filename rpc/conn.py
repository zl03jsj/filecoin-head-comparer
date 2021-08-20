import json
import requests
from threading import Thread
import logging


class _thread(Thread):
    def __init__(self, func, args=()):
        super(_thread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            self.result = self.func(*self.args)
        except Exception as e:
            print("method:%s, params:%s\n", self.args[0], self.args[1])
            logging.exception(e)

    def get_result(self):
        try:
            Thread.join(self)
            return self.result
        except Exception as e:
            print("get result, failed:%s\n" % (e))
            return None


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
        return {'cids': cids,
                'blocks': res['Blocks'],
                'height': blks["Height"] if "Height" in blks else blks['height'],
                'name': self.name}

    def post(self, method, params):
        if not isinstance(method, str):
            raise ValueError('method required to be string')
        self.payload["method"] = method

        if params and not isinstance(params, list):
            raise ValueError('params required to be list')

        self.payload["params"] = params

        res = requests.request("POST", self.url, headers=self.header,
                               data=json.dumps(self.payload))
        if res.status_code != 200:
            print("unexpected, post to %s failed, status_code=%d" % (
                self.name, res.status_code))
            return
        if method == 'Filecoin.ChainHead':
            return self.parse_head(json.loads(res.text)["result"])
        else:
            json_obj = json.loads(res.text)
            if 'result' in json_obj:
                return json_obj['result']
            else:
                print("error : method:%s, params:%s, message:%s" % (
                    method, params, json_obj['error']['message']))
                return json_obj['error']


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
        threads = []
        for idx, val in enumerate(self.conns):
            t = _thread(func=val.post, args=(method, params))
            threads.append(t)
            t.start()
        for index, t in enumerate(threads):
            ress.append(t.get_result())
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

        print('|--ChainHead, height:%d, block:%d, %s' % (
            res[0]['height'], len(res[0]['cids']),
            '100-%match' if matchs else 'mis-match'))

        if False == matchs:
            for idx, v in enumerate(res):
                print("|- %-20s: height:%d, block:%d" % (
                    v['name'], v['height'], len(v['cids'])))

        print('\n')

        return res, matchs

    def do_check_result(self, tipset, method, params, displayName=None):
        check_info = {'tipset': tipset, 'method': method, 'params': params}
        res = self.post(check_info['method'], check_info['params'])

        matchs = True

        d_0 = json.dumps(res[0])

        for idx in range(1, len(res)):
            d = json.dumps(res[idx])
            if d_0 != d:
                matchs = False
                break

        print('|-- method:%s, height:%d, result:%s\nparams:%s\n' % (
            displayName if displayName is not None else method,
            tipset['height'], '100-%match' if matchs else 'mis-match', params))
        return res, matchs

    def do_check_ChainGetRandomnessFromTickets(self, tipset):
        addr = "f0128788"
        params = [tipset['cids'], 0, tipset['height'] - 10, addr]
        for idx in range(1, 9):
            params[1] = idx
            self.do_check_result(tipset, 'Filecoin.ChainGetRandomnessFromTickets', params)

    def do_check_CheckChainGetRandomnessFromBeacon(self, tipset):
        addr = "f0128788"
        params = [tipset['cids'], 0, tipset['height'] - 10, addr]
        for idx in range(1, 9):
            params[1] = idx
            self.do_check_result(tipset, 'Filecoin.ChainGetRandomnessFromBeacon', params)

    def do_check_ChainGetBlockMessages(self, tipset):
        for _, blk in enumerate(tipset['blocks']):
            self.do_check_result(tipset, "Filecoin.ChainReadObj", [blk['Messages']],
                                 displayName='BlockMessages')
            self.do_check_result(tipset, 'Filecoin.ChainReadObj',
                                 [blk['ParentMessageReceipts']],
                                 displayName='ParentMessageReceipts')

    def do_check_StateMinerSectors(self, tipset, addresses):
        for _, miner in enumerate(addresses):
            self.do_check_result(tipset, "Filecoin.StateMinerRecoveries",
                                 [miner, tipset['blocks'][0]['Parents']])
            self.do_check_result(tipset, "Filecoin.StateMinerFaults",
                                 [miner, tipset['blocks'][0]['Parents']])
            self.do_check_result(tipset, "Filecoin.StateGetActor",
                                 [miner, tipset['blocks'][0]['Parents']])

    def do_check_StateMinerSectorAllocated(self, tipset, addresses, start, end):
        for _, miner in enumerate(addresses):
            for i in range(start, end):
                self.do_check_result(tipset, "Filecoin.StateMinerSectorAllocated",
                                     [miner, i, tipset['blocks'][0]['Parents']])

    def do_check_StateMinerProvingDeadline(self, tipset, addresses):
        for _, miner in enumerate(addresses):
            res, matches = self.do_check_result(tipset,
                                                "Filecoin.StateMinerProvingDeadline",
                                                [miner, tipset['blocks'][0]['Parents']])
            if matches == True:
                if not 'Index' in res[0].keys():
                    for idx, v in enumerate(res):
                        print('Filecoin.StateMinerProvingDeadline unexpected result, address:%s, key: Index not exist, the result is : %s' % (addresses[idx], v))
                    return

                self.do_check_result(tipset, "Filecoin.StateMinerPartitions",
                                     [miner, res[0]['Index'],
                                      tipset['blocks'][0]['Parents']])
