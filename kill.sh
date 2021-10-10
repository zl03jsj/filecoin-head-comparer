function get_process() {
  pid=$(ps -ef | grep -v 'grep' | grep -E '.*python.*chain_head_detect.py' | sed -n 1p | awk '{print $2}')
  echo ${pid}
}


function kill_all() {
  pid=$(get_process)
  while [ "$pid" != "" ]; do
    echo kill process $pid
    kill -9 $pid
    pid=$(get_process)
  done
}
