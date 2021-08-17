#! /usr/bin python3
import json
from rpc.conn import _conn, _conns
from time import sleep

with open("./config.json", 'r') as f:
    conn_cfgs = json.load(f)

conns = _conns()

for c in conn_cfgs:
    conns.insert(_conn(c['name'], c['url'], c['token']))

catch_exeptions = True
if __name__ == "__main__":
    print('____________check chain head match with following nodes____________')
    for idx, c in enumerate(conns.conns):
        print("%d, %s, %s" % (idx, c.name, c.url))
    print('-------------------------------------------------------------------\n')

    while True:
        if catch_exeptions:
            try:
                conns.do_check_heads()
            except Exception as e:
                print(e)
        else:
            conns.do_check_heads()
        sleep(4)
