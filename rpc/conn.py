import json
import requests
from threading import Thread
import logging
from functools import reduce
import operator as op


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
            res_obj = json.loads(res.text)
            print("unexpected, post to %-15s failed, status_code=%d, error=%s" % (
                self.name, res.status_code, res_obj['error']))

            return
        if method == 'Filecoin.ChainHead':
            return self.parse_head(json.loads(res.text)["result"])
        else:
            json_obj = json.loads(res.text)
            if 'result' in json_obj:
                return json_obj['result']
            else:
                print("|- method:%s returns error\n|- params:%s\n|- message:%s" % (
                    method, params, json_obj['error']['message']))
                return json_obj['error']


def to_josn(d, exclude=[]):
    for k in exclude:
        if k in d.keys(): del d[k]
    return json.dumps(d, default=lambda o: o.__dict__, sort_keys=True).lower()


class _conns_manager:
    conns = []

    def __init__(self, conns=None):
        if not conns:
            return

        if not isinstance(conns, list):
            raise ValueError('conns required to be list[conn]')

        for c in conns:
            if not isinstance(c, _conns_manager):
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
                print("|- %+20s: height:%d, block:%d" % (
                    v['name'], v['height'], len(v['cids'])))

        print()
        return res, matchs

    def do_check_result(self, tipset, method, params, displayName=None, skip=[]):
        check_info = {'tipset': tipset, 'method': method, 'params': params}
        res = self.post(check_info['method'], check_info['params'])

        matchs = True

        d_0 = to_josn(res[0], skip)

        for idx in range(1, len(res)):
            d = to_josn(res[idx], skip)
            if d_0 != d: matchs = False

        print('|-- method:%s, height:%d, result:%s\n|-- params:%s' % (
            displayName if displayName is not None else method,
            tipset['height'], '100-%match' if matchs else 'mis-match', params))

        if not matchs:
            for idx, r in enumerate(res):
                print('%d->%s' % (idx, r))
            print('\n')

        return res[0] if matchs else res, matchs

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

    def do_check_StateMinerStuff(self, tipset, addresses):
        tsk = tipset['cids']
        params = ['', tsk]

        for _, miner in enumerate(addresses):
            params[0] = miner
            self.do_check_result(tipset, 'Filecoin.StateMinerPower', params)
            self.do_check_result(tipset, "Filecoin.StateMinerRecoveries", params)
            self.do_check_result(tipset, "Filecoin.StateMinerFaults", params)
            self.do_check_result(tipset, "Filecoin.StateMinerInfo", params)
            self.do_check_result(tipset, "Filecoin.StateMinerAvailableBalance", params)
            # for con in self.conns:
            #     if con.name == 'lotus': break
            # if con is None: continue
            #
            # state = con.post('Filecoin.StateReadState', params)
            # if 'State' not in state.keys(): continue
            # pms_id = state['State']['PreCommittedSectors']

    def do_check_StateGetActor(self, tipset, addresses):
        for _, actor in enumerate(addresses):
            self.do_check_result(tipset, "Filecoin.StateGetActor",
                                 [actor, tipset['blocks'][0]['Parents']])

    def do_check_StateMinerSectorAllocated(self, tipset, addresses, start, end):
        for _, miner in enumerate(addresses):
            for i in range(start, end):
                parent_key = tipset['blocks'][0]['Parents']
                res, matches = self.do_check_result(tipset,
                                                    "Filecoin.StateMinerSectorAllocated",
                                                    [miner, i, parent_key])
                if matches:
                    self.do_check_result(tipset,
                                         'Filecoin.StateSectorGetInfo',
                                         [miner, i, parent_key])

    def do_check_StateMinerSectorsStuff(self, tipset, addresses):
        parent_key = tipset['blocks'][0]['Parents']
        for _, miner in enumerate(addresses):
            deadlines, matches = self.do_check_result(tipset,
                                                      "Filecoin.StateMinerProvingDeadline",
                                                      [miner, parent_key])
            if matches == True:
                if not 'Index' in deadlines.keys():
                    for idx, v in enumerate(deadlines):
                        print(
                            'error, method:Filecoin.StateMinerProvingDeadline, address:%s, key: Index not exist\nresult : %s' % (
                                addresses[idx], v))
                    return

                partitions, _ = self.do_check_result(tipset,
                                                     "Filecoin.StateMinerPartitions",
                                                     [miner, deadlines['Index'],
                                                      parent_key])
                if partitions is None:
                    continue

                for pt in partitions:
                    params = [miner, pt['ActiveSectors'], parent_key]
                    sectors, matches = self.do_check_result(tipset,
                                                            'Filecoin.StateMinerSectors',
                                                            params)
                    # if not matches: continue
                    # for sector in sectors:
                    #     params = [miner, sector['SectorNumber'], parent_key]
                    #     sector_pre_commit_info, matches = self.do_check_result(tipset,
                    #                                                            'Filecoin.StateSectorPreCommitInfo',
                    #                                                            params)
                    #     if not matches: continue
                    #     self.do_check_result(tipset,
                    #                          "Filecoin.StateMinerInitialPledgeCollateral",
                    #                          [miner, sector_pre_commit_info['Info'],
                    #                           parent_key])

    def do_check_WalletBalance(self, tipset, actors):
        actors = actors.copy()
        actors.extend(['f01000', 'f1ojyfm5btrqq63zquewexr4hecynvq6yjyk5xv6q',
                       'f3qfrxne7cg4ml45ufsaxqtul2c33kmlt4glq3b4zvha3msw4imkyi45iyhcpnqxt2iuaikjmmgx2xlr5myuxa'], )
        for actor in actors:
            balance, _ = self.do_check_result(tipset,
                                              'Filecoin.WalletBalance', [actor])

    def load_message_template(self):
        if hasattr(self, 'message'):
            return self.message.copy()

        with open("./message.json", 'r') as f:
            self.message = json.load(f)
            self.message["GasLimit"] = 0
            self.message["GasFeeCap"] = "0"
            self.message["GasPremium"] = "0"
            f.close()
            return self.message

    def do_check_EstimateGas(self, tipset):
        msg = self.load_message_template()
        actor, matches = self.do_check_result(tipset, 'Filecoin.StateGetActor',
                                              [msg['From'], tipset['cids']])
        if not matches:
            print("|- check StateGetActor mis-match, 'estimategase' won't continue")
            return

        msg['Nonce'] = actor['Nonce']
        msg, matches = self.do_check_result(tipset, 'Filecoin.GasEstimateMessageGas',
                                            [msg,
                                             {'MaxFee': '0', 'GasOverEstimation': 0},
                                             tipset['cids']], skip=['CID'])
        print("|- EstimateMessageGas returns:%s\n" % (msg))
        return

    def do_check_getbaseinfo(self, tipset, miners=[]):
        miners.extend(['f02438', 'f0131822'])
        block = tipset['blocks'][0]
        for miner in miners:
            self.do_check_result(tipset, 'Filecoin.MinerGetBaseInfo',
                                 [miner, block['Height'], block['Parents']])
        return

    def do_check_StateCirculatingSupply(self, tipset):
        params = [tipset['cids']]
        self.do_check_result(tipset, 'Filecoin.StateCirculatingSupply', params)
        self.do_check_result(tipset, 'Filecoin.StateVMCirculatingSupplyInternal', params)

    def do_check_ChainGetParentReceipts(self, tipset):
        params = [tipset['cids'][0]]
        self.do_check_result(tipset, 'Filecoin.ChainGetParentReceipts', params)

    def do_check_StateReadState_venus_not_exist_this_api(self, tipset, actors):
        params = ['', tipset['cids']]
        for actor in actors:
            params[0] = actor
            self.do_check_result(tipset, 'Filecoin.StateReadState', params)

# MinerCreateBlock(context.Context, *BlockTemplate)(*types.BlockMsg, error)
# SyncSubmitBlock(ctx context.Context, blk * types.BlockMsg) error
# ChainGetParentReceipts(ctx context.Context, blockCid cid.Cid) ([] * types.MessageReceipt, error)
# StateMinerPower(context.Context, address.Address, types.TipSetKey)(*MinerPower, error)
# StateMinerInitialPledgeCollateral(context.Context, address.Address, miner.SectorPreCommitInfo, types.TipSetKey)( types.BigInt, error)
# StateMinerAvailableBalance(context.Context, address.Address, types.TipSetKey)( types.BigInt, error)
# StateSectorPreCommitInfo(context.Context, address.Address, abi.SectorNumber, types.TipSetKey)(miner.SectorPreCommitOnChainInfo, error)
# StateWaitMsg(ctx context.Context, cid cid.Cid, confidence uint64, limit abi.ChainEpoch, allowReplaced bool) (*MsgLookup, error)
# StateMarketBalance(context.Context, address.Address, types.TipSetKey)(MarketBalance, error)
