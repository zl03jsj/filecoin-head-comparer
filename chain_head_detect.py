#! /usr/bin python3
import json
from rpc.manager import _conns_manager
from time import sleep
import logging
import sys, getopt

miners = ['f02438', 'f0688165', 'f0724216', "f0128788", "f0127595", "f0123261", "f0135467", "f0142720", ]
accounts = ["f3qzprefkeragndcicaqgztojarm4pzohn7swwqtmtcx42wykpgxtz6rtpn7xsderun5kigfopv3tydhddx4na",
    "f3sfyonhd3apsolzlpl5uy2a7j7jyktekp7v365l2uqo4chmmf7zmkmsry5qru562yhetnruzflmcnldwow6uq"]

with open("./config.json", 'r') as f:
    conn_cfgs = json.load(f)

    if 'miners' in conn_cfgs:
        miners = conn_cfgs['miners']

    if 'accounts' in conn_cfgs:
        accounts = conn_cfgs['accounts']

    f.close()

conn_manager = _conns_manager(conn_cfgs)

actors = miners.copy()
actors.extend(accounts)

print('____________check chain head match with following nodes____________')
for idx, c in enumerate(conn_manager.conns):
    print("%d, %s, %s" % (idx, c.name, c.base_url))
print('-------------------------------------------------------------------\n')


def loop_check_heads():
    while True:
        try:
            conn_manager.do_check_heads()
        except Exception as e:
            logging.exception(e)
        sleep(3)


def loop_check_apis():
    dur = 3
    tipset = {'cids': ''}
    is_api_matched = False
    while True:
        try:
            heads, same_height, matched = conn_manager.do_check_heads()
            if not matched:
                sleep(dur)
                continue
            elif tipset is not None and tipset['cids'] == heads[0]['cids']:
                if matched:
                    print("|-- chain head doesn't change, don't need to compare again")
                    sleep(dur)
                    continue
                elif is_api_matched:
                    print("|-- api check result is already be true, don't need to compare again")
                    sleep(dur)
                    continue

            tipset = heads[0]
            conn_manager.do_check_BeaconGetEntry(tipset)
            conn_manager.do_check_ChainGetPath(tipset)
            conn_manager.do_check_GetBaseInfo(tipset, miners)
            conn_manager.do_check_ChainGetRandomnessFromTickets(tipset)
            conn_manager.do_check_CheckChainGetRandomnessFromBeacon(tipset)
            conn_manager.do_check_StateMinerStuff(tipset, miners)
            conn_manager.do_check_EstimateGas(tipset)
            conn_manager.do_check_WalletBalance(tipset, actors)
            conn_manager.do_check_StateCirculatingSupply(tipset)
            conn_manager.do_check_StateGetActor(tipset, miners)
            conn_manager.do_check_StateLookupRobustAddress(tipset)
            if not conn_manager.is_check_slow_apis(): continue
            conn_manager.do_check_StateMinerSectorsStuff(tipset, miners)
            conn_manager.do_check_StateMinerSectorAllocated(tipset, miners, 900000000000, 900000000010)
            conn_manager.do_check_StateMinerSectorAllocated(tipset, miners, 0, 1172579)
            conn_manager.do_check_ChainGetParentReceipts(tipset)
            conn_manager.do_check_ChainGetBlockMessages(tipset)
            print("|-- ---------------------round finished!---------------------\n")
        except Exception as e:
            logging.exception(e)
        sleep(dur)


def main(argv):
    inputfile = ''
    outputfile = ''
    try:
        opts, args = getopt.getopt(argv, "hia:", ["api="])
    except getopt.GetoptError:
        print('test.py -i <inputfile> -o <outputfile>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('python3 -u ./chain_head_detect.py > chain_head.log 2>&1 &')
            sys.exit()
        elif opt in ("-a", "--api="):
            check_api = arg


if __name__ == "__main__":
    if len(sys.argv) == 1:
        loop_check_heads()
    else:
        loop_check_apis()
