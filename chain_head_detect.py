#! /usr/bin python3
import json
from rpc.conn import _conn, _conns
from time import sleep
import logging

with open("./config.json", 'r') as f:
    conn_cfgs = json.load(f)
    f.close()

conns = _conns()

for c in conn_cfgs:
    conns.insert(_conn(c['name'], c['url'], c['token']))

addresses = ["f0128788", "f0127595", "f0123261",
             "f3qzprefkeragndcicaqgztojarm4pzohn7swwqtmtcx42wykpgxtz6rtpn7xsderun5kigfopv3tydhddx4na",
             "f3qzprefkeragndcicaqgztojarm4pzohn7swwqtmtcx42wykpgxtz6rtpn7xsderun5kigfopv3tydhddx4na", ]

if __name__ == "__main__":
    print('____________check chain head match with following nodes____________')
    for idx, c in enumerate(conns.conns):
        print("%d, %s, %s" % (idx, c.name, c.url))
    print('-------------------------------------------------------------------\n')

    while True:
        try:
            heads, matched = conns.do_check_heads()
            if matched:
                tipset = heads[0]
                # conns.do_check_ChainGetRandomnessFromTickets(tipset)
                # conns.do_check_CheckChainGetRandomnessFromBeacon(tipset)
                # conns.do_check_ChainGetBlockMessages(tipset)
                # conns.do_check_StateMinerSectors(tipset, addresses)
                # conns.do_check_StateMinerSectorAllocated(tipset, addresses, 900, 1000)
                # conns.do_check_StateMinerSectorAllocated(tipset, addresses, 900000000000,
                #                                          900000000010)
                conns.do_check_StateMinerProvingDeadline(tipset, addresses)
        except Exception as e:
            logging.exception(e)
        sleep(4)
