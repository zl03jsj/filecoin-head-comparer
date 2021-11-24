from rpc.venus_client import _venus_client
from rpc.lotus_client import _lotus_client
import json
import os
import sys

venus_cfg = {}
lotus_cfg = {}
block_cid = None

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
    block_cid = cfg['block_cid']
    print("venus url:%s" % (venus_cfg['url']))
    print("lotus url:%s" % (lotus_cfg['url']))

    venus_client = _venus_client(venus_cfg['url'], venus_cfg['token'])
    lotus_client = _lotus_client(lotus_cfg['url'], lotus_cfg['token'])
    only_cmp_receipt = cfg['only_cmp_receipt']


def oldversionCheck(height, block_cid):
    if None==block_cid:
        head = lotus_client.chain_get_tipset_by_height(height)['result']
        block_cid = head['Cids'][0]

    v_msgs = venus_client.chain_get_parent_messages(block_cid)['result']
    l_msgs = lotus_client.chain_get_parent_messages(block_cid)['result']

    print('''
    message count, venus:%d, lotus:%d
     ''' % (len(v_msgs), len(l_msgs)))

    v_receipts = venus_client.chain_get_parent_receipts(block_cid)['result']
    l_receipts = lotus_client.chain_get_parent_receipts(block_cid)['result']

    for idx in range(0, len(v_msgs)):
        msg = l_msgs[idx]
        v_rect = v_receipts[idx]
        l_rect = l_receipts[idx]
        isok = v_rect['gasUsed'] == l_rect['GasUsed']

        print(
            'idx:%3d, cid:%s, %s' % (
                idx, msg['Cid']['/'], 'ok' if isok else 'not equals'))

        if not isok:
            print('''
    venus-receipt: %s
    lotus_receitp: %s
    
    messsage: %s
    
    ''' % (v_rect, l_rect, json.dumps(msg['Message'], indent=6)))
            break

    # venus_client.chain_get_tipset_by_height()
    # venus_client.chain_get_parent_messages()


def main(argv):
    if len(argv) > 1:
        height = int(argv[1])
    else:
        print('''
    epoch height is required.
    python3 ./exec_trace_cmp.py <epoch height>
    ''')
        return

    if only_cmp_receipt:
        return oldversionCheck(height, block_cid)

    venus_exec_trace = venus_client.replay_tipset(height=height)
    lotus_exec_trace = lotus_client.replay_tipset(height=height)
    cmp_exec_traces(height, lotus_exec_trace, venus_exec_trace)


show_enable_trace_on_lotus = True


def cmp_exec_traces(height, l_result, v_result):
    global show_enable_trace_on_lotus
    if l_result['Root'] == v_result['StateRoot']:
        print('''
    Venus and lotus got the same state root(%s) after apply tipset(%d)
''' % (
            l_result['Root']['/'], v_result[
                'Epoch']))
    else:
        print(
            "Warning: state root not equals after apply tipset(%d) venus(%s) != lotus(%s)" % (
                v_result['Epoch'], l_result['Root']['/'], v_result['StartRoot']['/']))

    vmts = v_result['MsgRets']
    lvts = l_result['Trace']

    print('''
    start compile tipset(%d) traces
    venus total message count(contain implicit)= %d
    lotus total message count(contain implicit)= %d
    ''' % (height, len(vmts), len(lvts)))

    func_cmp = cmp_traces
    if lvts[0]['ExecutionTrace']['GasCharges'] is None:
        print('''
    Have you opened lotus execution traces?
    Set variable 'EnableGasTracing' = true in './chain/vm/runtime.go',
    Then re-compile to open execution trace on lotus.
    Till exec-traces is enable, we can only compare 'receipt' of messages.
    ''')
        func_cmp = cmp_receipts

    for idx, lmt in enumerate(lvts[:len(lvts) - 1]):
        vmt = vmts[idx]
        if not func_cmp(idx, lmt, vmt):
            break

    return


def check_befor_cmp(idx, l_msg, v_msg):
    v_msg_cid = v_msg['MsgCid']

    if is_implict_message(v_msg['Msg']):
        return True, True, l_msg['MsgCid']['/']

    # if v_msg_cid is None: return True, True, l_msg['MsgCid']

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


def is_implict_message(v_msg):
    return v_msg['from'] == 'f00' or v_msg['from'] == 't00'


def is_cron_message(v_msg):
    return v_msg['from'] == 'f00' and v_msg['to'] == 'f03' and v_msg['method'] == 2


def cmp_traces(msg_idx, l_msg, v_msg):
    (equals, implicit, msg_cid) = check_befor_cmp(msg_idx, l_msg, v_msg)
    if not equals: return False

    msg = v_msg['Msg']

    func_cmp = lambda lt, vt: lt['Name'] == vt['Name'] and lt['tg'] == vt['tg']

    v_chargs = v_msg['ExecutionTrace']['GasCharges']
    l_chargs = l_msg['ExecutionTrace']['GasCharges']
    if is_cron_message(msg):
        print('-> message:%d is a cron message: <-' % (msg_idx))
        v_traces = [x for x in v_chargs if x['Name'] == 'OnSetActor']
        l_traces = [x for x in l_chargs if x['Name'] == 'OnSetActor']
        func_cmp = lambda x, y: x['ex'] == y['ex']
    else:
        v_traces = [x for x in v_chargs if x['tg'] != 0]
        l_traces = [a for a in l_chargs if a['tg'] != 0]

    l_trace_size, v_trace_size = len(l_traces), len(v_traces)
    min_size = min(l_trace_size, v_trace_size)

    isok = True

    for idx in range(0, min_size):
        l_trace, v_trace = l_traces[idx], v_traces[idx]
        if not func_cmp(l_trace, v_trace):
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
        print("-> implicit message(%s -> %s, method : %d, nonce:%d) <-" % (
            msg['from'], msg['to'], msg['method'], msg['nonce']))

    print('idx:%3d, Compare msg(%s) state-root: %s execution-traces: %s' % (
        msg_idx, msg_cid, v_msg['StateRootAfterApply']['/'], 'ok' if isok else 'failed'))

    return isok


def cmp_receipts(idx, l_msg, v_msg):
    (equals, implicit, msg_cid) = check_befor_cmp(idx, l_msg, v_msg)
    if not equals: return False
    l_receipt = l_msg['ExecutionTrace']['MsgRct'] if l_msg['ExecutionTrace'][
                                                         'MsgRct'] is not None else l_msg[
        'MsgRct']
    v_receipt = v_msg['ExecutionTrace']['MsgRct'] if v_msg['ExecutionTrace'][
                                                         'MsgRct'] is not None else v_msg[
        'MsgRct']
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
