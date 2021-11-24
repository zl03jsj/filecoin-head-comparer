from rpc.conn import _conn


class _venus_client(_conn):
    def __init__(self, url, token, debug=False):
        super().__init__("venus", url, token, debug)

    def replay_tipset(self, height):
        ts = self.chain_get_tipset_by_height(height)['result']
        # msgs = self.chain_get_messages_in_tipset(ts['Keys'])
        return self.post("ReplayTipset", [ts['Key']])['result']
