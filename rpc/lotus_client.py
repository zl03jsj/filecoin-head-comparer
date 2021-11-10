from rpc.conn import _conn


class _lotus_client(_conn):
    def __init__(self, url, token):
        super().__init__("lotus", url, token)

    def replay_tipset(self, height):
        ts = self.chain_get_tipset_by_height(height)['result']
        # msgs = self.chain_get_messages_in_tipset(ts['Cids'])
        return self.post("ReplayTipset", [ts['Cids']])['result']

    def chain_get_messages_in_tipset(self, ts_key):
        msgs = super().chain_get_messages_in_tipset(ts_key)['result']
        return [x['Message'] for x in msgs]

    # func (a *StateAPI) StateCompute(ctx context.Context, height abi.ChainEpoch, msgs []*types.Message, tsk types.TipSetKey) (*api.ComputeStateOutput, error) {
    def state_compute(self, ts, msgs):
        return self.post("StateCompute", [ts['Height'], msgs, ts['Cids']])['result']
