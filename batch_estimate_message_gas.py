from rpc.conn import _conn
import json
import os
import sys

client_cfg = {}
message_cfg = {}


def is_miner_actor(code):
    return code == "bafkqaetgnfwc6nrpon2g64tbm5sw22lomvza"


with open("./gas_estimate_client.json", 'r') as f:
    cfg = json.load(f)
    if 'client' not in cfg:
        print("must have 'client' section in configuration")
        os.exit(0)
    # if 'messages' not in cfg:
    #     print("must have 'messages' section in configuration")
    #     os.exit(0)
    client_cfg = cfg['client']
    # messages_cfg = cfg['messages']

client = _conn(client_cfg['name'], client_cfg['url'], client_cfg['token'])


def main(argv):
    # ts_key = [{'/': 'bafy2bzacecat364rqdch32yrs45vzmbk5bdw7i6ngitu5ikxpmp74piro4l54'},
    #           {'/': 'bafy2bzacecpc2zmxo5pu72su5s3mbool3lumzw65uqvmwch2jppgn6vyelwma'},
    #           {'/': 'bafy2bzacecxh3lesu7c3uy3ji7curyrcgjb6v757iwqozit2zb3xm4y3d3e6c'}, ]
    head = client.chain_get_tipset_by_height(1250512)['result']

    ts_key, block0, = head['Key'], head['Blocks'][0]
    parent_key, block_cid = block0['parents'], ts_key[0]

    msgs = client.chain_get_parent_messages(cid=block_cid)['result']
    # print(msgs[0])
    receipts = client.chain_get_parent_receipts(cid=block_cid)['result']

    p_ts = client.chain_get_tipset(parent_key)['result']
    p_ts_block0 = p_ts['Blocks'][0]
    pp_key = p_ts_block0['parents']
    print(pp_key)

    # find the first message which 'to' is a miner
    f = 'f3woc2abngxqf3ondoiwnepzvo5rueqd7nbfpngbntntjy4b4e6axyipvzdh53qriqcon6jqm6fie2psd56y5q'
    t = 'f0469055'

    # for idx, msg in enumerate(msgs):
    #     res = client.state_get_actor(msg['Message']['to'])['result']
    #     if is_miner_actor(res['Code']['/']):
    #         f = msg['Message']['from']
    #         break
    print("-> there are %d messages in tipset : %d" % (len(msgs), p_ts_block0['height']))

    (from_nonce, msgs, receipts, cids) = extract_estimate_messages(t, msgs, receipts)

    if False:
        res = client.exec_tipste(ts_key=parent_key)
        print('-> exec_tipset: %s' % (ts_key))
        exit(0)

    if False:
        res = client.chain_estimate_message_gas(msgs[0]['Msg'], parent_key)
        print('-> esitmate message : %s -> gaslimit : %s\n' % (
            cids[0]['/'], res['result']['gasLimit']))
        exit(0)

    # print(msgs[0])
    # print(msgs)

    # GasBatchEstimateMessageGas
    estimates = client.batch_estmate_message_gas(from_nonce, msgs, parent_key)['result']
    estimates = [x['Msg'] for x in estimates]

    for idx, msg in enumerate(estimates):
        print("idx:%d, from:%s, nonce:%d, estimate gaslimit:%d, gasused:%d, equals : %s" % (
            idx, msg['from'], msg['nonce'], msg['gasLimit'], receipts[idx]['gasUsed'],
            "ok" if msg['gasLimit'] == receipts[idx]['gasUsed'] else "failed"))


def extract_estimate_messages(t, msgs, receipts):
    # type EstimateMessage struct { Msg * Message, Spec * MessageSendSpec }
    estimates = []
    recpts = []
    cids = []
    previous = {}
    for idx, msg in enumerate(msgs):
        # if msg['Message']['to'] != t:
        #     continue
        c = msg['Message'].copy()
        # c['gasLimit'] = 0
        estimates.append({"Msg": c, 'Spec': {"MaxFee": "0", 'GasOverEstimation': 1.0}})
        recpts.append(receipts[idx])
        cids.append(msg['Cid'])

    from_nonce = estimates[0]['Msg']['nonce']

    return from_nonce, estimates, recpts, cids


if __name__ == "__main__":
    main(sys.argv)
