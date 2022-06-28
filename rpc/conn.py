import json
import traceback

import requests

from rpc.utils import is_error, dict_exists_path


class _conn:
    def __init__(self, name, url, token, debug=False):
        self.name = name
        self.base_url = url
        self.header = None
        self.debug = debug

        if token and len(token) != 0:
            self.header = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

        self.payload = {"jsonrpc": "2.0", "id": 1, }

    def parse_head(self, res):
        # [x['/'] for x in ((res['Cids'] if 'Cids' in res else res['Key']))]
        cids = res['Key'] if 'Key' in res else (res['Cids'] if 'Cids' in res else None)
        blks = res['Blocks'][0]
        return {'cids': cids, 'blocks': res['Blocks'], 'height': blks["Height"] if "Height" in blks else blks['height'],
                'name': self.name}

    def url(self, version="v0"):
        return "{base_url}{slash}rpc/{method_ver}".format(base_url=self.base_url,
            slash='' if self.base_url[len(self.base_url) - 1] == '/' else '/', method_ver=version)

    def post(self, method, params, name_space='Filecoin', version="v0"):
        # {"id": 1, "jsonrpc": "2.0", "params": [{"offset_range": {"start": 0, "count": 25}, "method": "PreCommitSector"}],
        #  "method": "filscan.GetMessages"}
        method = name_space + '.' + method

        if not isinstance(method, str):
            raise ValueError('method required to be string')
        self.payload["method"] = method

        if params and not isinstance(params, list):
            raise ValueError('params required to be list')

        self.payload["params"] = params
        res = requests.request("POST", self.url(version=version), headers=self.header, data=json.dumps(self.payload))
        if self.debug:
            print(''' 
-> http post information: <-
   method: %s, param:%s
   http response: %s
            ''' % (method, params, res.text))
        if res.status_code != 200:
            print("unexpected, post to %-15s failed, status_code=%d, text:%s" % (self.name, res.status_code, res.text))

            return
        if method == 'Filecoin.ChainHead':
            return self.parse_head(json.loads(res.text)["result"])
        else:
            json_obj = json.loads(res.text)

            if is_error(json_obj):
                return {'name': self.name, 'result': json_obj['error']}
            else:
                return {'name': self.name, 'result': json_obj['result']}

    # GasBatchEstimateMessageGas(ctx context.Context, estimateMessages[] * types.EstimateMessage, fromNonce uint64, tsk types.TipSetKey) ([] * types.EstimateResult, error)
    def batch_estmate_message_gas(self, nonce, messages, tipset_key):
        return self.post('GasBatchEstimateMessageGas', [messages, nonce, tipset_key])

    def exec_tipste(self, ts_key):
        return self.post("ExecTipset", [ts_key])

    def chain_estimate_message_gas(self, message, ts_key):
        return self.post('GasEstimateMessageGas', [message, {'MaxFee': "0", 'GasOverEstimation': 1.0}, ts_key])

    # ChainGetParentMessages(ctx context.Context, bcid cid.Cid) ([]apitypes.Message, error)
    def chain_get_parent_messages(self, cid):
        return self.post('ChainGetParentMessages', [cid])

    def chain_get_parent_receipts(self, cid):
        return self.post('ChainGetParentReceipts', [cid])

    # ChainGetParentReceipts(ctx context.Context, bcid cid.Cid) ([] * types.MessageReceipt, error)
    # def chain_get_parent_receipts(self, cid):
    #     return self.post('ChainGetParentReceipts', [cid])

    def chain_get_head(self):
        return self.post("ChainHead", [])

    def chain_get_tipset(self, ts_key):
        return self.post("ChainGetTipSet", [ts_key])

    def chain_get_block(self, block_cid):
        return self.post("ChainGetBlock", [block_cid])

    def chain_get_tipset_by_height(self, height):
        return self.post("ChainGetTipSetByHeight", [height, None])

    # ChainGetMessagesInTipset(ctx context.Context, key types.TipSetKey) ([]apitypes.Message, error)
    def chain_get_messages_in_tipset(self, ts_key):
        return self.post("ChainGetMessagesInTipset", [ts_key])

    def chain_get_message(self, msg_id):
        return self.post("ChainGetMessage", [msg_id])

    # StateSearchMsg(ctx context.Context, from types.TipSetKey, msg cid.Cid, limit abi.ChainEpoch, allowReplaced bool) (*MsgLookup, error) //perm:read
    def state_search_message(self, msg_id):
        return self.post("StateSearchMsg", [msg_id])

    def list_miners(self):
        return self.post("StateListMiners", [None])

    def state_get_actor(self, addr):
        return self.post("StateGetActor", [addr, None])


def remove_key(v, exclude):
    if v is None or isinstance(v, int) or isinstance(v, str):
        return v
    else:
        v = v.copy()
    if isinstance(v, dict):
        dict_remove_key(v, exclude)
    elif isinstance(v, slice) or isinstance(v, list):
        for idx, e in enumerate(v):
            dict_remove_key(e, exclude)
    return v


def dict_remove_key(v, exclude):
    if len(exclude) == 0 or not isinstance(v, dict): return
    for k in exclude:
        if k in v.keys(): del v[k]


def to_josn(v, exclude=[]):
    v = remove_key(v, exclude)
    return json.dumps(v, default=lambda o: o.__dict__, sort_keys=True).lower()


class _precommit_sector_provider:
    def __init__(self, url):
        self.url = url
        self.conn = _conn("precommitsectors_provider", self.url, "")

    def precommitsectors(self):
        # curl https://api.filscan.io:8700/rpc/v1 -X POST -H "Content-Type: application/json"  -d '{"id":1,"jsonrpc":"2.0","params":[{"offset_range":{"start":0,"count":5},"method":"PreCommitSector"}],"method":"filscan.GetMessages"}'
        res = self.conn.post("GetMessages", [{"offset_range": {"start": 0, "count": 5}, "method": "PreCommitSector"}],
            name_space='filscan', version='v1')
        res = res['result']['data']
        if not isinstance(res, list) and not isinstance(res, slice): return None
        return [[s['to'], s['args']['SectorNumber']] for s in res]

    def precommitsectorsV2(self):
        res = requests.get('https://filfox.info/api/v1/message/list?pageSize=5&page=0&method=PreCommitSector')
        if res.status_code != 200:
            return None
        res = json.loads(res.text)


def check_response(res):
    is_err = 'message' in res
    if is_err:
        lines = traceback.format_stack()
        line = lines[len(lines) - 2]
        print('''
  %s
    response err message:%s''' % (line, res['message']))
    return is_err
