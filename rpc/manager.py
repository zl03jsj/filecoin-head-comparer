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
    sector_provider = _precommit_sector_provider()

    def __init__(self, cfg):
        for c in cfg['urls']:
            if 'enable' in c.keys() and c['enable'] == 'no': continue
            self.insert(_conn(c['name'], c['url'], c['token']))
        self.always_display_params = cfg['always_display_params']

    def insert(self, c):
        if not isinstance(c, _conn):
            raise ValueError('conns required to be list[conn]')
        self.conns.append(c)

    def post(self, method, params=None):
        method = 'Filecoin.' + method
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
            '100-%match' if matchs else 'mis-match'))

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

    def do_check_result(self, tipset, method, params, displayName=None, skip=[], checker=None):
        check_info = {'tipset': tipset, 'method': method, 'params': params}
        res = self.post(check_info['method'], check_info['params'])

        matchs = True

        d_0 = to_josn(res[0]['result'], skip)

        for idx in range(1, len(res)):
            d = to_josn(res[idx]['result'], skip)
            if checker is not None or False:
                matchs = False if not checker(res[0]['result'], res[idx]['result']) else matchs
            elif d_0 != d:
                matchs = False

        print('|--  method:%s, height:%d, API->%s\n' % (
            displayName if displayName is not None else method,
            tipset['height'], '100-%match' if matchs else 'mis-match'))

        if not matchs or self.always_display_params:
            print('|---- params:%s' % (params))
            for idx, r in enumerate(res):
                print('|---- %-16s->%s' % (r['name'], r['result']))
            print('\n')

        return res[0] if matchs else res, matchs

    def do_check_ChainGetRandomnessFromTickets(self, tipset):
        addr = "f0128788"
        params = [tipset['cids'], 0, tipset['height'] - 10, addr]
        for idx in range(1, 9):
            params[1] = idx
            self.do_check_result(tipset, 'ChainGetRandomnessFromTickets', params)

    def do_check_CheckChainGetRandomnessFromBeacon(self, tipset):
        addr = "f0128788"
        params = [tipset['cids'], 0, tipset['height'] - 10, addr]
        for idx in range(1, 9):
            params[1] = idx
            self.do_check_result(tipset, 'ChainGetRandomnessFromBeacon', params)

    def do_check_ChainGetBlockMessages(self, tipset):
        for _, blk in enumerate(tipset['blocks']):
            self.do_check_result(tipset, "ChainReadObj", [blk['Messages']], displayName='BlockMessages')
            self.do_check_result(tipset, 'ChainReadObj', [blk['ParentMessageReceipts']], displayName='ParentMessageReceipts')

    def do_check_StateMinerStuff(self, tipset, addresses):
        miners = addresses[:2]
        tsk = tipset['cids']
        block = tipset['blocks'][0]
        params = ['', tsk]

        self.do_check_result(tipset, "StateVMCirculatingSupplyInternal", [tsk])
        # self.do_check_result(tipset, "StateCirculatingSupply", [tsk])

        for _, miner in enumerate(miners):
            params[0] = miner
            _, m = self.do_check_result(tipset, 'StateMinerPower', params)
            _, m = self.do_check_result(tipset, 'MinerGetBaseInfo', [miner, block['Height'], block['Parents']])
            _, m = self.do_check_result(tipset, "StateMinerInfo", params)
            _, m = self.do_check_result(tipset, "StateMinerAvailableBalance", params)
            _, m = self.do_check_result(tipset, "StateMinerRecoveries", params)
            _, m = self.do_check_result(tipset, "StateMinerFaults", params)
            _, m = self.do_check_result(tipset, "StateMinerProvingDeadline", params)
            _, m = self.do_check_result(tipset, "StateMinerDeadlines", params)
            _, m = self.do_check_result(tipset, "StateMinerSectorCount", params)
            _, m = self.do_check_result(tipset, "StateMarketBalance", params)

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
        for _, actor in enumerate(addresses):
            self.do_check_result(tipset, "StateGetActor", [actor, tipset['cids']])

    def do_check_StateMinerSectorAllocated(self, tipset, addresses, start, end):
        check_count = 10
        for _, miner in enumerate(addresses):
            for i in range(start, end, int((end - start) / check_count)) if end - start > check_count else 1:
                parent_key = tipset['blocks'][0]['Parents']
                res, matches = self.do_check_result(tipset, "StateMinerSectorAllocated", [miner, i, parent_key])
                if matches and res['result'] is True:
                    # res, matches = self.do_check_result(tipset, "StateSectorPreCommitInfo", [miner, i, parent_key])
                    res, matches = self.do_check_result(tipset, 'StateSectorGetInfo', [miner, i, parent_key])
                    if res['result'] is not None and matches:
                        print('|--    StateSectorGetInfo:%s' % (res['result']))

    def do_check_StateMinerSectorsStuff(self, tipset, addresses):
        miners = addresses[:2]
        parent_key = tipset['blocks'][0]['Parents']
        for _, miner in enumerate(miners):
            deadlines, matches = self.do_check_result(tipset, "StateMinerProvingDeadline", [miner, parent_key])
            if matches == True:
                deadlines = deadlines['result']
                if not 'Index' in deadlines.keys():
                    for idx, v in enumerate(deadlines):
                        print('error, method:StateMinerProvingDeadline, address:%s, key: Index not exist\nresult : %s' % (
                            addresses[idx], v))
                    return
                partitions, _ = self.do_check_result(tipset, "StateMinerPartitions", [miner, deadlines['Index'], parent_key])
                if partitions is None:
                    continue
                for pt in partitions['result']:
                    params = [miner, pt['ActiveSectors'], parent_key]
                    self.do_check_result(tipset, 'StateMinerSectors', params)

    def do_check_WalletBalance(self, tipset, actors):
        actors = actors.copy()
        actors.extend(['f01000', 'f1ojyfm5btrqq63zquewexr4hecynvq6yjyk5xv6q',
                       'f3qfrxne7cg4ml45ufsaxqtul2c33kmlt4glq3b4zvha3msw4imkyi45iyhcpnqxt2iuaikjmmgx2xlr5myuxa'], )
        for actor in actors:
            balance, _ = self.do_check_result(tipset, 'WalletBalance', [actor])

    def load_message_template(self):
        msgtype = "don't know"
        if hasattr(self, 'message'):
            return self.message[msgtype].copy()

        with open("./message.json", 'r') as f:
            self.message = json.load(f)
            m = self.message[msgtype]
            m["GasLimit"] = 0
            m["GasFeeCap"] = "0"
            m["GasPremium"] = "0"

            f.close()
            return m

    def do_check_EstimateGas(self, tipset):
        msg = self.load_message_template()
        actor, matches = self.do_check_result(tipset, 'StateGetActor', [msg['From'], tipset['cids']])
        if not matches:
            print("|- check StateGetActor mis-match, 'estimategase' won't continue")
            return

        msg['Nonce'] = actor['result']['Nonce']
        msg, matches = self.do_check_result(tipset, 'GasEstimateMessageGas',
                                            [msg, {'MaxFee': '0', 'GasOverEstimation': 0}, tipset['cids']], skip=['CID'])
        print("|- EstimateMessageGas returns:%s\n" % (msg))
        return

    def do_check_getbaseinfo(self, tipset, miners=[]):
        miners.extend(['f02438', 'f0131822'])
        block = tipset['blocks'][0]
        for miner in miners:
            self.do_check_result(tipset, 'MinerGetBaseInfo', [miner, block['Height'], block['Parents']])
        return

    def do_check_StateCirculatingSupply(self, tipset):
        params = [tipset['cids']]
        self.do_check_result(tipset, 'StateCirculatingSupply', params)
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
            res, matches = self.do_check_result(tipset, 'StateSectorPreCommitInfo', sct, checker=checker)
            if matches:
                self.do_check_result(tipset, 'StateMinerInitialPledgeCollateral', [sct[0], res['result']['Info'], tipset['cids']])

    # MinerCreateBlock(context.Context, *BlockTemplate)(*types.BlockMsg, error)
    # SyncSubmitBlock(ctx context.Context, blk * types.BlockMsg) error
    # ChainGetParentReceipts(ctx context.Context, blockCid cid.Cid) ([] * types.MessageReceipt, error)
    # StateMinerPower(context.Context, address.Address, types.TipSetKey)(*MinerPower, error)
    # StateMinerInitialPledgeCollateral(context.Context, address.Address, miner.SectorPreCommitInfo, types.TipSetKey)( types.BigInt, error)
    # StateMinerAvailableBalance(context.Context, address.Address, types.TipSetKey)( types.BigInt, error)
    # StateSectorPreCommitInfo(context.Context, address.Address, abi.SectorNumber, types.TipSetKey)(miner.SectorPreCommitOnChainInfo, error)
    # StateWaitMsg(ctx context.Context, cid cid.Cid, confidence uint64, limit abi.ChainEpoch, allowReplaced bool) (*MsgLookup, error)
    # StateMarketBalance(context.Context, address.Address, types.TipSetKey)(MarketBalance, error)

    # StateMinerPower
    # StateMinerAvailableBalance
