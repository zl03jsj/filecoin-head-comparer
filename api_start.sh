source kill.sh
kill_all
export PATH="$PATH:/Users/zl/workspace/filecoin-head-comparer/grc"
nohup python3 -u ./chain_head_detect.py api > api.log 2>&1 &
grc -c ./grc.conf tail -f ./api.log
kill_all
