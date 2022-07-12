#!/usr/bin python3
import getopt
import sys
import traceback

from replacer import message_replacer
from utils import _args


def usage():
    print('''
usage:

-- replace messages in message pool:
./do_replace -g <gas_premium> -i no \\
    --gas-fee-cap=<message-gas-fee-cap> \\
    --lotus-svr=<lotus-server-url> \\
    --node-url=<node-url> \\
    --node-token=<node-token> \\
    --max-replace-count=<max-replace-message-count>

-i, --interactive   是否启用交模式, 可选, 默认为:启用. 不启用:['n', 'no', 'false', 'f', 0], 其它输入为:启用
-g, --gas-premium   替换消息使用的gas-premium. 可选. 默认值为0. 如果为0时,自动填充为(old-gas-premium * 1.25)
--gas-fee-cap       消息的gas-fee-cape
--lotus-svr         lotus-server的url
--node-url          lotus节点的url
--node-token        lotus节点的token
--control-idx       miner控制地址的序号, 可选. 如果不设置, 或者设置了错误的值, 将通过交互式提示用户选择.
--max-replace-count 最多替换的消息数量. 可选. 默认值为 100
-h,--help           show help string

-- example:
./do_replace.py --gas_premium=7350000000 \\
    --gas-fee-cap=7360000000 \\
    --node-url=http://192.168.200.126:1234 \\
    --lotus-svr=192.168.200.126:3456 \\
    --node-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJBbGxvdyI6WyJyZWFkIiwid3JpdGUiLCJzaWduIiwiYWRtaW4iXX0.O2Gmh1Yn2uje7OgxP9UzbA5Rwgb758DuDxveAQLyr0Q \\
    --control-idx=0 \\
    --interactive=false \\
    --max-replace-count=25

-- show help:
./do_replace.py -h
''')


def main():
    short_args_fmt = "hg:c:i:"
    loong_args_fmt = ["help", 'control-idx=', "lotus-svr=", "node-url=", "node-token=", "gas-premium=", "gas-fee-cap=",
        "max-replace-count=", 'interactive=']
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], short_args_fmt, loong_args_fmt)
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    args = _args()

    for opt, value in opts:
        if opt in ("-h", "--help"):
            args.is_help = True
            break
        if opt in "--lotus-svr":
            args.lotus_svr = value
            continue
        if opt in ('-c', "--control-idx"):
            args.ctrl_idx = int(value)
            continue
        if opt in ('--gas-premium', '-g'):
            args.gas_premium = int(value)
            continue
        if opt in ('--interactive', '-i'):
            value = value.lower()
            args.interactive = not value in ['false', 'f', '0', 'no', 'n']
            continue
        if opt in '--gas-fee-cap':
            args.gas_fee_cap = int(value)
            continue
        if opt in '--node-url':
            args.lotus = value
            continue
        if opt in '--node-token':
            args.lotus_token = value
            continue
        if opt in '--max-replace-count':
            args.max_count = int(value)
            continue

    if args.is_help:
        usage()
        return

    isok, err_info = args.is_valid()
    if not isok:
        print('--> 参数错误:\n\t{message}'.format(message=err_info))
        usage()
        return

    try:
        do_replace(args)
    except KeyboardInterrupt as e:
        print('\n--> 用户退出!\n')
    except Exception as e:
        print(traceback.format_exc())


def do_replace(args: _args):
    replacer = message_replacer(svr_url=args.lotus_svr,
        node_url=args.lotus,
        node_token=args.lotus_token)

    replacer.do_replace(args)


if __name__ == "__main__":
    main()
