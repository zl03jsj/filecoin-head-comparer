from rpc.venus_client import _venus_client
from rpc.lotus_client import _lotus_client
from rpc.conn import check_response
import json
import os
import sys

venus_cfg = {}
lotus_cfg = {}
block_cid = None

messages = [{"/": "bafy2bzacebqzmce7ryytifmionufwip6ycxekmq7riummnkjckpicxy2tl542"},
            {"/": "bafy2bzaceda46lersgjmxyt5ohh747b63zrktvjxkqz2gae3bxkpeuirncjug"},
            {"/": "bafy2bzacebc3tn24otl7kwrtclkewmz7n52wug3gtrp5y2c4pkzw2jbsr7m34"},
            {"/": "bafy2bzacedvmkbmagfxqa6zsqq7vrbdejbuhvlkmfsfwq7imd7mmwqwm5vwda"},
            {"/": "bafy2bzacedqpayyhuh3257ddy5pjy6dyl2wzyxjeqo4mhhgcqp3pzrfm6ptum"},
            {"/": "bafy2bzacea7d3pidjkrsfqyptjurhfzd3pzn5xtg6jwiediklkheeih5s5ai2"},
            {"/": "bafy2bzacecadvykxtaoijrej6vfnpyudy4cqem3fu74b5maifgomzuj2s4beu"},
            {"/": "bafy2bzaceddzm4rziqwgtjdjskgjnpocx6smte2tkej7yxwqowhbm2cx7a2ii"},
            {"/": "bafy2bzaced6xealtmbg4jmtahtd3nkpbqyyz4iygnyxgczhsjkoryynb2u5uy"},
            {"/": "bafy2bzacecm6y4dpjrxauoyvptmqkvdrignjmlkb5wulu3uaamjna7gqhdmb2"},
            {"/": "bafy2bzacedfi335si2jgli53piswegld54fp5vqfbxe3jzxzwfejlj4jedttm"},
            {"/": "bafy2bzacealvmlg3nxhfz7ok4e3mlm6zexqvv2qrddzuzudvthovsyfo5busq"},
            {"/": "bafy2bzacecyso7rjqep5uo3zcqv6u2m5p54p25c3kobedxrcugvo6hzh54ohc"},
            {"/": "bafy2bzaceauwc5kfjmchspkiozemco4j636sqoj33grevn4b7vo527erdmagu"},
            {"/": "bafy2bzacea7nglbjn3lv354s2ydt44kzhecarezgpvxcnmqvpr6jvu5zek7ne"},
            {"/": "bafy2bzaced76cuzmjlvfn4rho47o2dx3psuzgh2kulqotkchqyqqi5dm7vyok"},
            {"/": "bafy2bzacedflsijew7h35vrtkkcq36oerhwlycs6mxwarz2wm4anku6ul2fbq"},
            {"/": "bafy2bzacedlc3exicm4jz6hdgilpoa2szzk3iovl3fifyt5cvuxo5zumxx4zs"},
            {"/": "bafy2bzacebyvmrxtynl72qqgrwu3q6mnwd7b2igvwwikh7cussll4bwlsqpy4"},
            {"/": "bafy2bzacear32z3taevptweb4ulolo4rtnyguuo73lzyowmzls6ff42bhbziw"},
            {"/": "bafy2bzaceca4prkb2oqks4cs725cdyjb47ex5wdat6yp3sogib5hkn5vcncsu"},
            {"/": "bafy2bzacecfzupggl37u6xouegkkyil43iuk537evpfylb3tv2cmoizl56jiq"},
            {"/": "bafy2bzaceaztftt42liz3bzn7olfob6dhbh6frdy42zf6mx4ixsgrrn2jfvhq"},
            {"/": "bafy2bzacecmsrcizhqk3q3ay2elv46eu67nfa2okw7krzkdwya7yrjy2oklpc"}, ]

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

    if 'block_cid' in cfg:
        block_cid = cfg['block_cid']

    print('''
    venus url:%s
    lotus url:%s
     ''' % (venus_cfg['url'], lotus_cfg['url']))

    debug = False
    if 'debug_mode' in cfg:
        debug = cfg['debug_mode']

    venus_client = _venus_client(venus_cfg['url'], venus_cfg['token'], debug)
    lotus_client = _lotus_client(lotus_cfg['url'], lotus_cfg['token'], debug)
    only_cmp_receipt = cfg['only_cmp_receipt']


def only_check_receipts(height, block_cid=None):
    if block_cid is None:
        print('    use height:%s in configurations' % (height))
        head = lotus_client.chain_get_tipset_by_height(height)['result']
        block_cid = head['Cids'][0]
        height = lotus_client.chain_get_block(block_cid)['result']['Height']
    else:
        print('    use block_cid:%s in configurations', block_cid['/'])

    v_msgs = venus_client.chain_get_parent_messages(block_cid)['result']
    if check_response(v_msgs): return

    l_msgs = lotus_client.chain_get_parent_messages(block_cid)['result']
    if check_response(l_msgs): return

    print('''
    message count, venus:%d, lotus:%d, height=%s, block_cid=%s
     ''' % (len(v_msgs), len(l_msgs), height, block_cid))

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
        return only_check_receipts(height, block_cid)

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
