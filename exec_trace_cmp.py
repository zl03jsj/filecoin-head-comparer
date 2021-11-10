from rpc.venus_client import _venus_client
from rpc.lotus_client import _lotus_client
import json
import os
import sys

venus_cfg = {}
lotus_cfg = {}

with open("./cfg_exec_trace.json", 'r') as f:
    cfg = json.load(f)
    if 'venus' not in cfg:
        print("must have 'venus' section in configuration")
        os.exit(0)
    if 'lotus' not in cfg:
        print("must have 'venus' section in configuration")
        os.exit(0)
    venus_cfg = cfg['venus']
    lotus_cfg = cfg['lotus']
    print("venus url:%s" % (venus_cfg['url']))
    print("lotus url:%s" % (lotus_cfg['url']))

    venus_client = _venus_client(venus_cfg['url'], venus_cfg['token'])
    lotus_client = _lotus_client(lotus_cfg['url'], lotus_cfg['token'])


def main(argv):
    if len(argv) > 1:
        height = int(argv[1])
    else:
        print('''
    epoch height is required.
    python3 ./exec_trace_cmp.py <epoch height>
    ''')
        return

    lotus_exec_trace = lotus_client.replay_tipset(height=height)
    venus_exec_trace = venus_client.replay_tipset(height=height)
    cmp_exec_traces(lotus_exec_trace, venus_exec_trace)


show_enable_trace_on_lotus = True


def cmp_exec_traces(l_result, v_result):
    global show_enable_trace_on_lotus
    if l_result['Root'] == v_result['StateRoot']:
        print("Venus and lotus got the same state root(%s) after apply tipset(%d)" % (
            l_result['Root']['/'], v_result[
                'Epoch']))
    else:
        print(
            "Warning: state root not equals after apply tipset(%d) venus(%s) != lotus(%s)" % (
                v_result['Epoch'], l_result['Root']['/'], v_result['StartRoot']['/']))

    vmts = v_result['MsgRets']
    lvts = l_result['Trace']

    func_cmp = cmp_traces
    if lvts[0]['ExecutionTrace']['GasCharges'] is None:
        print('''
    Have you opened lotus execution traces?
    Set variable 'EnableGasTracing' = true in './chain/vm/runtime.go',
    Then re-compile to open execution trace on lotus.
    Till exec-traces is enable, we can only compare 'receipt' of messages.
    ''')
        func_cmp = cmp_receipts

    for idx, lmt in enumerate(lvts):
        vmt = vmts[idx]
        if not func_cmp(idx, lmt, vmt):
            break

    return


def check_befor_cmp(idx, l_msg, v_msg):
    v_msg_cid = v_msg['MsgCid']
    if v_msg_cid is None: return True, True, l_msg['MsgCid']

    msg_cid_equals = l_msg['Msg']['CID']['/'] == v_msg['MsgCid']['/']
    msg_cid = ""
    if not msg_cid_equals:
        print('''
    idx:%d, Message Cid not equals:
    lotus message:%s, from:%s, nonce:%d
    venus message:%s, from:%s, nonce:%d
    ''' % (idx, l_msg['MsgCid'], l_msg['Msg']['From'], l_msg['Msg']['Nonce'],
           v_msg['MsgCid'], v_msg['ExecutionTrace']['Msg']['from'],
           v_msg['ExecutionTrace']['Msg']['nonce']))
    else:
        msg_cid = l_msg['Msg']['CID']['/']

    return msg_cid_equals, False, msg_cid


def is_cron_message(v_msg):
    return msg['from'] == 'f00' and msg['to'] == 'f03' and msg['method'] == 3


def cmp_traces(msg_idx, l_msg, v_msg):
    (equals, implicit, msg_cid) = check_befor_cmp(msg_idx, l_msg, v_msg)
    if not equals: return False

    msg = v_msg['Msg']

    if is_cron_message(msg):
        print('-> this is a cron message, just compare receipts <-')
        return cmp_receipts(msg_idx, l_msg, v_msg)

    v_traces = [x for x in v_msg['ExecutionTrace']['GasCharges'] if x['tg'] != 0]

    l_traces = [a for a in l_msg['ExecutionTrace']['GasCharges'] if a['tg'] != 0]
    # l_traces.extend(
    #     [w for w in sum([z for z in [y['GasCharges'] for y in [x for x in l_msg[
    #         'ExecutionTrace']['Subcalls']]]], []) if w['tg'] != 0])

    l_trace_size, v_trace_size = len(l_traces), len(v_traces)
    min_size = min(l_trace_size, v_trace_size)

    isok = True

    for idx in range(0, min_size):
        l_trace, v_trace = l_traces[idx], v_traces[idx]
        if not cmp_trace(l_trace, v_trace):
            print('''
    message trace(%d) not equals:
    message details : cid:%s, from:%s, to:%s, nonce:%d
-----> lotus_trace:---------------
%s  
-----> venus_trace:---------------
%s
''' % (idx, msg_cid, msg['from'], msg['to'], msg['nonce'],
       json.dumps(l_trace, indent=4, ensure_ascii=False),
       json.dumps(v_trace, indent=4, ensure_ascii=False)))
            isok = False
            break

    if l_trace_size != v_trace_size:
        isok = False

    if implicit:
        print("implicit message(%s -> %s %d, nonce:%d)" % (
            msg['from'], msg['to'], msg['method'], msg['nonce']))

    print('idx:%3d, Compare msg(%s) stateAfterApply: %s execution-traces: %s' % (
        msg_idx, msg_cid, v_msg['StateRootAfterApply']['/'], 'ok' if isok else 'failed'))

    return isok


def cmp_trace(l_trace, v_trace):
    return l_trace['Name'] == v_trace['Name'] and l_trace['tg'] == v_trace['tg']


def cmp_receipts(idx, l_msg, v_msg):
    (equals, implicit, msg_cid) = check_befor_cmp(idx, l_msg, v_msg)
    if not equals: return False
    l_receipt = l_msg['MsgRct']
    v_receipt = v_msg['MsgRct']
    msg = v_msg['Msg']

    if implicit:
        print("implicit message(%s -> %s : %d, nonce:%d)" % (
            msg['from'], msg['to'], msg['method'], msg['nonce']))

    ok = l_receipt['ExitCode'] == v_receipt['exitCode'] and l_receipt['GasUsed'] == \
         v_receipt['gasUsed']

    print(
        'idx:%3d, Compare %smsg(%s) receipts, %s' % (idx,
                                                     'implicit ' if implicit else '',
                                                     msg_cid, 'ok' if ok else 'failed'))
    return ok


if __name__ == "__main__":
    main(sys.argv)
