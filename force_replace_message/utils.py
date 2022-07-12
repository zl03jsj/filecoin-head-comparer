#! /usr/bin python3

max_times = 3


def must_input(prompt="", must_be=[]):
    ipt = input(prompt)
    idx = max_times

    if must_be is None or len(must_be) == 0:
        return ipt

    while ipt not in must_be and idx >= 1:
        ipt = input(
            "--> please input:[{value:s}]? >> ".format(value="/".join(must_be)))
        idx = idx - 1

    if ipt not in must_be:
        print("inputs must in: {value:s}".format(value="/".join(must_be)))
        exit(0)

    return ipt


def must_select(prompt="", must_be=[]):
    print(prompt)
    if len(must_be) == 0:
        print('--> 可以选择的内容为空,程序退出..')

    for idx, v in enumerate(must_be):
        print('    idx: %d, %s' % (idx, v))

    index = int(must_input('--> 请输入选择的序号:', [str(i) for i in range(0, len(must_be))]))
    return must_be[index]


def find_message(msgs=[], address=[]) -> list:
    first_find_addr = None
    outs = []
    for msg in msgs:
        if first_find_addr is None:
            if msg['Message']['From'] in address:
                first_find_addr = msg['Message']['From']
                outs.append(msg['Message'])
        elif msg['From'] == first_find_addr: outs.append(msg)

    if first_find_addr is not None:
        print('--> 实际使用的地址为:%s\n', first_find_addr)

    return outs


class _args:
    def __init__(self, lotus_svr=None, gas_premium=0,
            lotus_url=None, lotus_token='', max_replace_count=100, ctrl_idx=-1, interactive=True) -> None:
        self.is_help = False
        self.lotus_svr = lotus_svr
        self.gas_premium = gas_premium
        self.gas_fee_cap = 0
        self.lotus = lotus_url
        self.lotus_token = lotus_token
        self.max_count = max_replace_count
        self.ctrl_idx = ctrl_idx
        self.interactive = interactive

    def as_dict(self) -> dict:
        return {
            "is_help": self.is_help,
            "lotus_server": self.lotus_svr,
            "lotus": self.lotus,
            "lotus-token": self.lotus_token,
            "gas_fee_cap": self.gas_fee_cap,
            "gase_premium": self.gas_premium,
            "max_replace_count": self.max_count,
            "ctrl_idx": self.ctrl_idx,
            "interactive": self.interactive
        }

    def is_valid(self) -> (bool, str):
        if self.is_help:
            return True
        if not (isinstance(self.lotus_svr, str) or len(self.lotus_svr) == 0):
            return False, 'lotus-svr:{url}设置错误'.format(url=self.lotus_svr)
        if not (isinstance(self.lotus, str) or len(self.lotus) == 0):
            return False, 'node-url:{url}设置错误'.format(url=self.lotus)
        if not (isinstance(self.gas_premium, int) or self.gas_premium < 0):
            return False, 'gas-premium:{value}, 设置错误'.format(value=self.gas_premium)
        if not (isinstance(self.gas_fee_cap, int) or self.gas_fee_cap <= 0):
            return False, 'gas-fee-cap:{value}, 设置错误'.format(value=self.gas_fee_cap)
        if self.max_count <= 0:
            return False, 'max-replace-count:{value}, 设置错误'.format(value=self.max_count)
        if not self.interactive and self.ctrl_idx < 0:
            return False, 'control-idx:{idx}, 设置错误,或者启用交互模式'.format(idx=self.ctrl_idx)
        return True, ''

def main() -> None:
    print('--> this is just a test.....\n')
    fruit = must_select('--> 选择你想吃的水果:', ['apple', 'banana', 'grape', 'peach'])
    print('--> 你选择的水果是: %s\n' % (fruit))

if __name__ == "__main__":
    main()
