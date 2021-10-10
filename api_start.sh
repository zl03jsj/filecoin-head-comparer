nohup python3 -u ./chain_head_detect.py api > api.log 2>&1 &
grc -c ./grc.conf tail -f ./api.log
