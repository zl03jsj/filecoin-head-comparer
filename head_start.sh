source ./kill.sh
kill_all
nohup python3 -u ./chain_head_detect.py > head.log 2>&1 &
grc -c ./grc.conf tail -f ./head.log
