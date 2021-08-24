#! /usr/bin python3
import json
from rpc.conn import _conn, _conns_manager
from time import sleep
import logging

with open("./config.json", 'r') as f:
    conn_cfgs = json.load(f)
    f.close()

conn_manager = _conns_manager()

for c in conn_cfgs:
    if 'enable' in c.keys() and c['enable'] == 'no': continue
    conn_manager.insert(_conn(c['name'], c['url'], c['token']))

miners = ['f02438', "f0128788", "f0127595", "f0123261", "f0135467", "f0142720"]
accounts = [
    "f3qzprefkeragndcicaqgztojarm4pzohn7swwqtmtcx42wykpgxtz6rtpn7xsderun5kigfopv3tydhddx4na",
    "f3sfyonhd3apsolzlpl5uy2a7j7jyktekp7v365l2uqo4chmmf7zmkmsry5qru562yhetnruzflmcnldwow6uq"]

actors = miners.copy()
actors.extend(accounts)

print('____________check chain head match with following nodes____________')
for idx, c in enumerate(conn_manager.conns):
    print("%d, %s, %s" % (idx, c.name, c.url))
print('-------------------------------------------------------------------\n')


def loop_check_heads():
    while True:
        try:
            conn_manager.do_check_heads()
        except Exception as e:
            logging.exception(e)
        sleep(4)


def loop_check_apis():
    while True:
        try:
            heads, matched = conn_manager.do_check_heads()
            if not matched:
                sleep(5)
                continue
            tipset = heads[0]
            # conn_manager.do_check_StateGetActor(tipset, miners)
            # conn_manager.do_check_EstimateGas(tipset)
            # conn_manager.do_check_WalletBalance(tipset, actors)
            # conn_manager.do_check_ChainGetParentReceipts(tipset)
            # conn_manager.do_check_ChainGetRandomnessFromTickets(tipset)
            # conn_manager.do_check_CheckChainGetRandomnessFromBeacon(tipset)
            # conn_manager.do_check_ChainGetBlockMessages(tipset)
            conn_manager.do_check_StateMinerStuff(tipset, miners)
            # conn_manager.do_check_StateMinerSectorsStuff(tipset, miners)
            # conn_manager.do_check_StateMinerSectorAllocated(tipset, miners, 900, 1000)
            # conn_manager.do_check_StateMinerSectorAllocated(tipset, miners, 900000000000, 900000000010)
            # conn_manager.do_check_getbaseinfo(tipset, miners)
            # conn_manager.do_check_WalletBalance(tipset, actors)
            # conn_manager.do_check_EstimateGas(tipset)
            # conn_manager.do_check_StateCirculatingSupply(tipset)
        except Exception as e:
            logging.exception(e)
        sleep(5)


if __name__ == "__main__":
    loop_check_apis()
    # loop_check_heads()
