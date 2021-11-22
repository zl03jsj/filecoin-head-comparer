from rpc.conn import _conn, _precommit_sector_provider, to_josn
from threading import Thread
import json
import time


class _thread(Thread):
    def __init__(self, func, args=()):
        super(_thread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            self.result = self.func(*self.args)
        except Exception as e:
            print("method:%s, params:%s, err:%s\n" % (self.args[0], self.args[1], e))

    def get_result(self):
        try:
            Thread.join(self)
            return self.result
        except Exception as e:
            print("get result, failed:%s\n" % (e))
            return None


class _conns_manager:
    conns = []
    cfg = {}

    def __init__(self, cfg):
        for c in cfg['urls']:
            if 'enable' in c.keys() and c['enable'] == 'no': continue
            self.insert(_conn(c['name'], c['url'], c['token']))
        self.always_display_params = cfg['always_display_params']
        self.sector_provider = _precommit_sector_provider(cfg['precommit_url'])
        self.cfg = cfg

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
            res = t.get_result()
            if res is not None:
                ress.append(res)
        return ress

    def do_check_heads(self):
        res = self.post("ChainHead")

        time_stamp = int(time.time())

        matchs = True
        d_0 = json.dumps((res[0]['height'], res[0]['cids']))

        for idx in range(1, len(res)):
            if res[idx] is None: continue
            d = json.dumps((res[idx]['height'], res[idx]['cids']))
            if d_0 != d:
                matchs = False
                break

        print('|-ChainHead, height:%d, block:%d, head->%s' % (
            res[0]['height'], len(res[0]['cids']),
            '100-%match\n' if matchs else 'mis-match'))

        same_height = True
        if False == matchs:
            away = time_stamp % 30
            if away > 12:
                print("|- this mis-matching will cause [INSULAR] block")
            for idx, v in enumerate(res):
                if v is None: continue
                if same_height and res[idx]['height'] != res[0]['height']:
                    same_height = False
                print("|- %+16s: height:%d, block:%d, away from time window:%d" % (
                    v['name'], v['height'], len(v['cids']), away))
            print()

        return res, same_height, matchs

    def do_check_result(self, tipset, method, params, displayName=None, skip=[],
                        checker=None):
        check_info = {'tipset': tipset, 'method': method, 'params': params}
        res = self.post(check_info['method'], check_info['params'])

        matchs = True
        errors = False

        d_0 = to_josn(res[0]['result'], skip)

        for idx in range(1, len(res)):
            if res[idx]['result'] is not None and isinstance(res[idx]['result'],
                                                             dict) and 'message' in \
                    res[idx]['result']:
                errors = True
            matchs = False if not matchs else (
                d_0 == to_josn(res[idx]['result'], skip) if checker is None else checker(
                    res[0]['result'], res[idx]['result']))

        print('|--  method:%s, height:%d, API->%s' % (
            displayName if displayName is not None else method,
            tipset['height'], (
                '100-%match\n' if not errors else '100-%match [but some errors occurs]') if matchs else 'mis-match'))

        if self.always_display_params or not matchs or errors:
            print('|    -params:%s' % (params))

        if not matchs or errors:
            for idx, r in enumerate(res):
                print('|    -%-16s-> %s' % (r['name'], r['result']))
            print('\n')

        return res[0] if matchs else res, matchs, errors

    def do_check_ChainGetRandomnessFromTickets(self, tipset, b644bytes="MjM0NQ=="):
        params = [tipset['cids'], 0, tipset['height'] - 10, b644bytes]
        for idx in range(1, 9):
            params[1] = idx
            self.do_check_result(tipset, 'ChainGetRandomnessFromTickets', params)

    def do_check_CheckChainGetRandomnessFromBeacon(self, tipset, b644bytes="MjM0NQ=="):
        params = [tipset['cids'], 0, tipset['height'] - 10, b644bytes]
        for idx in range(1, 9):
            params[1] = idx
            self.do_check_result(tipset, 'ChainGetRandomnessFromBeacon', params)

    def do_check_ChainGetBlockMessages(self, tipset):
        if not self.is_check_slow_apis(): return
        for _, blk in enumerate(tipset['blocks']):
            self.do_check_result(tipset, "ChainReadObj", [blk['Messages']],
                                 displayName='BlockMessages')
            self.do_check_result(tipset, 'ChainReadObj', [blk['ParentMessageReceipts']],
                                 displayName='ParentMessageReceipts')

    def do_check_StateMinerStuff(self, tipset, addresses):
        miners = addresses[:2]
        tsk = tipset['cids']
        block = tipset['blocks'][0]
        params = ['', tsk]

        def checker(x, y):
            keys = ['unknown actor code', 'actor not found']
            if x is None: return 'actor not found' in y['message']
            if 'message' in x:
                for k in keys:
                    if k in x['message'] and k in y['message']:
                        return True
            return to_josn(x) == to_josn(y)

        for _, miner in enumerate(miners):
            params[0] = miner
            self.do_check_result(tipset, 'StateMinerPower', params)
            self.do_check_result(tipset, 'MinerGetBaseInfo',
                                 [miner, block['Height'], block['Parents']])
            self.do_check_result(tipset, "StateMinerInfo", params, checker=checker)
            self.do_check_result(tipset, "StateMinerAvailableBalance", params)
            self.do_check_result(tipset, "StateMinerRecoveries", params)
            self.do_check_result(tipset, "StateMinerFaults", params)
            self.do_check_result(tipset, "StateMinerProvingDeadline", params)
            self.do_check_result(tipset, "StateMinerDeadlines", params)
            self.do_check_result(tipset, "StateMinerSectorCount", params,
                                 checker=checker)
            self.do_check_result(tipset, "StateMarketBalance", params)

        self.do_check_StateSectorPreCommitInfo(tipset)

        # don't check slow api
        # self.do_check_result(tipset, "StateMarketDeals", [tsk])
        # self.do_check_result(tipset, "StateListActors", [tsk])
        # self.do_check_result(tipset, "StateMinerActiveSectors", params)
        # for con in self.conns:
        #     if con.name == 'lotus': break
        # if con is None: continue
        # state = con.post('StateReadState', params)
        # if 'State' not in state.keys(): continue
        # pms_id = state['State']['PreCommittedSectors']

    def do_check_StateGetActor(self, tipset, addresses):
        def checker(x, y):
            return to_josn(x) == to_josn(
                y) if x is not None and 'message' not in x else 'actor not found' in x[
                'message'] and 'actor not found' in y['message']

        for _, actor in enumerate(addresses):
            self.do_check_result(tipset, "StateGetActor", [actor, tipset['cids']],
                                 checker=checker)

    def do_check_StateMinerSectorAllocated(self, tipset, addresses, start, end):
        check_count = 5
        for _, miner in enumerate(addresses):
            for i in range(start, end, int(
                    (end - start) / check_count) if end - start > check_count else 1):
                parent_key = tipset['blocks'][0]['Parents']
                res, matches, _ = self.do_check_result(tipset,
                                                       "StateMinerSectorAllocated",
                                                       [miner, i, parent_key])
                if matches and res['result'] is True:
                    res, matches, _ = self.do_check_result(tipset, 'StateSectorGetInfo',
                                                           [miner, i, parent_key])
                    if res['result'] is not None and matches:
                        print('|--    StateSectorGetInfo:%s' % (res['result']))

    def is_check_slow_apis(self):
        key = 'check_slow_apis'
        return False if key not in self.cfg else self.cfg[key]

    def do_check_StateMinerSectorsStuff(self, tipset, addresses):
        miners = addresses[:2]
        parent_key = tipset['blocks'][0]['Parents']
        for _, miner in enumerate(miners):
            deadlines, matches, _ = self.do_check_result(tipset,
                                                         "StateMinerProvingDeadline",
                                                         [miner, parent_key])
            if matches == True:
                deadlines = deadlines['result']
                if not 'Index' in deadlines.keys():
                    for idx, v in enumerate(deadlines):
                        print(
                            'error, method:StateMinerProvingDeadline, address:%s, key: Index not exist\nresult : %s' % (
                                addresses[idx], v))
                    return
                partitions, _, _ = self.do_check_result(tipset, "StateMinerPartitions",
                                                        [miner, deadlines['Index'],
                                                         parent_key])
                if partitions is None:
                    continue
                for pt in partitions['result']:
                    params = [miner, pt['ActiveSectors'], parent_key]
                    self.do_check_result(tipset, 'StateMinerSectors', params)

    def do_check_WalletBalance(self, tipset, actors):
        actors = actors.copy()
        # actors.extend(['f01000', 'f1ojyfm5btrqq63zquewexr4hecynvq6yjyk5xv6q',
        #                'f3qfrxne7cg4ml45ufsaxqtul2c33kmlt4glq3b4zvha3msw4imkyi45iyhcpnqxt2iuaikjmmgx2xlr5myuxa'], )
        for actor in actors:
            self.do_check_result(tipset, 'WalletBalance', [actor])

    def load_message_template(self):
        msgtype, tipset_key = "don't know", "ts_key"
        if hasattr(self, 'estimate_message'):
            return self.estiamte_message[msgtype].copy()

        with open("./message.json", 'r') as f:
            self.estiamte_message = json.load(f)
            m = self.estiamte_message[msgtype]
            m["GasLimit"] = 0
            m["GasFeeCap"] = "0"
            m["GasPremium"] = "0"
            return m

    def do_check_EstimateGas(self, tipset):
        msg = self.load_message_template()

        checker = lambda x, y: to_josn(x) == to_josn(
            y) if x is not None and 'message' not in x else 'actor not found' in x[
            'message'] and 'actor not found' in y['message']

        ts_key = tipset['cids']
        actor, matches, errors = self.do_check_result(tipset, 'StateGetActor',
                                                      [msg['From'], ts_key],
                                                      checker=checker)
        if not matches or errors:
            print(
                "|- check StateGetActor mis-match or error occours, 'estimategase' won't continue")
            return

        msg['Nonce'] = actor['result']['Nonce']
        self.do_check_result(tipset, 'GasEstimateMessageGas',
                             [msg, {'MaxFee': '0', 'GasOverEstimation': 1.25},
                              ts_key], skip=['CID'], checker=lambda l, v : l['GasLimit']==v['gasLimit'])
        return

    def do_check_ChainGetPath(self, tipset):
        # ChainGetPath(ctx context.Context, from types.TipSetKey, to types.TipSetKey) ([] * api.HeadChange, error) // perm: read

        def checker(x, y):
            for v in x:
                del v['Val']['Blocks']
                del v['Val']['Height']
            for v in y:
                del v['Val']['Blocks']
                v['Val']['Cids'] = v['Val']['Key']
                del v['Val']['Key']

            # xjson, yjson = to_josn(x), to_josn(y)
            # print("%s\n--\n%s\n" % (xjson, yjson))

            return to_josn(x) == to_josn(y)

        res, matches, err = self.do_check_result(tipset, 'ChainGetPath',
                                                 [[tipset['cids'][0]], tipset['cids']],
                                                 checker=checker)

    def do_check_GetBaseInfo(self, tipset, miners=[]):
        # miners.extend(['f02438', 'f0131822'])
        block = tipset['blocks'][0]
        for miner in miners:
            self.do_check_result(tipset, 'MinerGetBaseInfo',
                                 [miner, block['Height'], block['Parents']])
        return

    def do_check_StateCirculatingSupply(self, tipset):
        params = [tipset['cids']]
        # self.do_check_result(tipset, 'StateCirculatingSupply', params)
        self.do_check_result(tipset, 'StateVMCirculatingSupplyInternal', params)

    def do_check_ChainGetParentReceipts(self, tipset):
        params = [tipset['cids'][0]]
        self.do_check_result(tipset, 'ChainGetParentReceipts', params)

    def do_check_StateReadState_venus_not_exist_this_api(self, tipset, actors):
        params = ['', tipset['cids']]
        for actor in actors:
            params[0] = actor
            self.do_check_result(tipset, 'StateReadState', params)

    def do_check_StateSectorPreCommitInfo(self, tipset):
        sectors = self.sector_provider.precommitsectors()

        def checker(x, y):
            if x is None: return 'not exists' in y['message']
            return to_josn(x) == to_josn(y)

        for sct in sectors:
            sct.append(tipset['cids'])
            res, matches, _ = self.do_check_result(tipset, 'StateSectorPreCommitInfo',
                                                   sct,
                                                   checker=checker)
            if matches and res is not None and 'result' in res and 'Info' in res[
                'result']:
                params = [sct[0], res['result']['Info'], tipset['cids']]
                self.do_check_result(tipset, 'StateMinerInitialPledgeCollateral', params)
                self.do_check_result(tipset, "StateMinerPreCommitDepositForPower", params)

    # MinerCreateBlock(context.Context, *BlockTemplate)(*types.BlockMsg, error)
    # SyncSubmitBlock(ctx context.Context, blk * types.BlockMsg) error
    # ChainGetParentReceipts(ctx context.Context, blockCid cid.Cid) ([] * types.MessageReceipt, error)
    # StateMinerPower(context.Context, address.Address, types.TipSetKey)(*MinerPower, error)
    # StateMinerInitialPledgeCollateral(context.Context, address.Address, miner.SectorPreCommitInfo, types.TipSetKey)( types.BigInt, error)
    # StateMinerPreCommitDepositForPower(ctx context.Context, maddr address.Address, pci miner.SectorPreCommitInfo, tsk types.TipSetKey) (big.Int, error)
    # StateMinerAvailableBalance(context.Context, address.Address, types.TipSetKey)( types.BigInt, error)
    # StateSectorPreCommitInfo(context.Context, address.Address, abi.SectorNumber, types.TipSetKey)(miner.SectorPreCommitOnChainInfo, error)
    # StateWaitMsg(ctx context.Context, cid cid.Cid, confidence uint64, limit abi.ChainEpoch, allowReplaced bool) (*MsgLookup, error)
    # StateMarketBalance(context.Context, address.Address, types.TipSetKey)(MarketBalance, error)
    # StateMinerPower
    # StateMinerAvailableBalance
