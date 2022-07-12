#!/usr/bin python3
import http
from json import JSONDecodeError

import requests

from utils import must_input, must_select, _args


class _response:
    def __init__(self, data=None, msg=None, code=None):
        self.data = data
        self.msg = msg
        self.code = code

    def error(self) -> bool:
        return self.code == http.HTTPStatus.OK


class requester:
    def __init__(self, url=None, token=""):
        if url[len(url) - 1] != "/":
            url = url + "/"
        http_prefix = "http://"

        if len(url) > 4 and url[:4] != "http":
            url = http_prefix + url

        self.base_url = url
        self.token = token

    def json_rpc(self, method="", params=[], name_space='Filecoin', api_version='v1', headers={}):
        method = name_space + '.' + method
        params = {"id": 1, "json_rpc": "2.0",
            "params": params, "method": method}
        res = self.post(suffix_url="rpc/" + api_version,
            headers=headers, json=params)
        if 'error' in res:
            raise Exception("call {method:s} failed, message:{message:s}".format(
                method=method, message=res['error']['message']))
        return res['result']

    # post 返回dict, 如果http.status_code != ok 直接raise 错误. 否则返回{'data': ... }
    def post(self, suffix_url=None, headers={}, data=None, json=None) -> dict:
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json;charset=UTF-8'

        if 'Authorization' not in headers and len(self.token) > 0:
            headers['Authorization'] = 'Bearer ' + self.token

        res = requests.request("POST", self.base_url +
                                       suffix_url, headers=headers, data=data, json=json)

        if res.status_code != http.HTTPStatus.OK:
            raise Exception("post to {url:s} failed, http status code:{code:d}, message:{message:s}".
            format(url=suffix_url, code=res.status_code, message=res.text))

        out = {}
        try:
            out = res.json()
        except JSONDecodeError as e:
            out = {'data': res.text, }
        except Exception as e:
            out = {'data': res.text}

        return out


class lotus_server_client(requester):
    def __init__(self, url: str, token=""):
        super().__init__(url, token)

    def get_actor_info(self) -> dict:
        info = self.post("actor-info")
        if info['code'] != 0:
            raise Exception("get actor-info failed, code:{code:d}, msg:{msg:s}".
            format(code=info['code'], msg=info['msg']))
        return info['data']


class lotus_client(requester):
    def __int__(self, url: str, token: str):
        super().__init__(url, token)

    # StateMinerInfo(context.Context, address.Address, types.TipSetKey) (MinerInfo, error) //perm:read
    def state_miner_info(self, miner: str) -> dict:
        return self.json_rpc("StateMinerInfo", [miner, None], api_version='v0')

    # MpoolPending(context.Context, types.TipSetKey) ([]*types.SignedMessage, error) //perm:read
    def mpool_pending(self) -> list:
        return self.json_rpc("MpoolPending", [None])

    # WalletSignMessage(context.Context, address.Address, *types.Message) (*types.SignedMessage, error) //perm:sign
    def wallet_sign_message(self, msg) -> dict:
        return self.json_rpc("WalletSignMessage", params=[msg['From'], msg])

    # MpoolPush(context.Context, *types.SignedMessage) (cid.Cid, error) //perm:write
    def mpool_push(self, msg) -> str:
        cid = self.json_rpc("MpoolPush", params=[msg])
        return cid['/']

    # StateAccountKey(context.Context, address.Address, types.TipSetKey) (address.Address, error) //perm:read
    def state_account_key(self, actor_id) -> str:
        return self.json_rpc("StateAccountKey", params=[actor_id, None])


class message_replacer:
    def __init__(self, svr_url="", svr_token="", node_url="", node_token="") -> None:
        self.lts_svr_client = lotus_server_client(svr_url, svr_token)
        self.lts_client = lotus_client(node_url, node_token)

    def do_replace(self, args: _args):
        gas_premium = args.gas_premium
        fee_cap = args.gas_fee_cap
        max_count = args.max_count
        print('--> 从lotus-server(%s)获取miner地址:' % self.lts_svr_client.base_url)
        info = self.lts_svr_client.get_actor_info()
        miner = info['miner']
        print('--> miner地址:%s\n' % miner)

        print('--> 从lotus获取miner(%s)详细信息:' % self.lts_client.base_url)
        miner_info = self.lts_client.state_miner_info(miner)

        if False:
            control_actor_ids = miner_info['ControlAddresses']

            if control_actor_ids is None or len(control_actor_ids) == 0:
                print('\n--> miner(%s)的control-address为空, 程序退出!' % miner)
                exit(0)
            if 0 <= args.ctrl_idx < len(control_actor_ids):
                control_actor = control_actor_ids[args.ctrl_idx]
            elif args.interactive:
                control_actor = must_select(
                    '--> 请选择miner({m:s})的control-address:'.format(m=miner), control_actor_ids)
            else:
                print('--> 控制地址序号错误: idx=%d, count=%d, 程序退出!' % (args.ctrl_idx, len(control_actor_ids)))
                exit(0)

            control_addr = self.lts_client.state_account_key(
                actor_id=control_actor)
        else:
            control_actor = 't01001'
            control_addr = 't3wknhyskfndkpusfyl5o2uh4724radjxesfortxigrewti3izvjhsoucf5y22wuvq6ag4h2a62nzp42rfnq6q'

        print('--> 你选择的地址为: %s : %s\n' % (control_actor, control_addr))
        print("--> 替换消息, miner地址: %s, 控制地址: %s\n" % (miner, control_addr))

        pending_msgs = self.lts_client.mpool_pending()

        to_replace_msgs = [
            m['Message'] for m in pending_msgs if
            m['Message']['From'][1:] == control_addr[1:] or m['Message']['From'][1:] == control_actor[1:]]

        if len(to_replace_msgs) == 0:
            print('--> 没有找到需要替换的消息, 程序退出!')
            exit(0)

        count = min(max_count, len(to_replace_msgs))

        print("--> 共获取到: %d 条来自: %s 的消息, 本次将会替换: %d 条消息\n" %
              (len(to_replace_msgs), control_addr, count))

        to_replace_msgs = to_replace_msgs[:count]

        print("--> 开始执行replace之前, from地址:%s, 重新设置消息费用:" % (control_addr))
        self.reset_msg_fees(to_replace_msgs, gas_premium, fee_cap)

        if args.interactive:
            ipt = must_input('''
--> 批量替换消息有风险, 如果中间出错,无法回滚.
    你确定要执行以上消息批量替换操作[yes/no]? >> ''', ['yes', 'no'])

            if ipt != 'yes':
                print("--> 用户怂了, 选择不执行批量操作, 程序退出!")
                exit(0)

        print('\n--> 开始执行批量替换:')
        for one in to_replace_msgs:
            self.replace_one(one)

        print('--> 批量替换消息执行完成, 共替换了:%d条消息.\n' % len(to_replace_msgs))

    def reset_msg_fees(self, msgs, gas_premium, fee_cap):
        for msg in msgs:
            cur_min_premium = int(int(msg['GasPremium']) * 1.25 + 1)
            if gas_premium > 0:
                if cur_min_premium > gas_premium:
                    print('''
--> 错误: 消息: form: %s, nonce:%d
    设置的gas_premium(%d)小于最小replace gas_premium(%d = old_premium * 1.25 + 1)
--> 程序退出!
''' % (msg['From'], msg['Nonce'], gas_premium, cur_min_premium))
                    exit(0)
            else:
                gas_premium = cur_min_premium

            if fee_cap <= gas_premium:
                print('''
--> 错误: 消息: from: %s, nonce:%d
    gas_fee_cap(%d)小于gas_premium(%d)
--> 程序退出!
    ''' % (msg['From'], msg['Nonce'], fee_cap, gas_premium))
            old_gas_premium = int(msg['GasPremium'])
            msg['GasPremium'] = str(gas_premium)
            msg['GasFeeCap'] = str(fee_cap)

            print("    nonce=%8d, gas_premium(%d -> %d), gas_fee_cap=%d, gas_limit=%d"
                  % (msg['Nonce'], old_gas_premium, gas_premium, fee_cap, msg['GasLimit']))

    def replace_one(self, msg):
        signed = self.lts_client.wallet_sign_message(msg)
        self.lts_client.mpool_push(signed)

        print('\t消息:%8d, 成功!' % (msg['Nonce']))
