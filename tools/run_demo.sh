#!/usr/bin/env bash
# Record one demo run headless: start the warehouse sim, record both demo
# cameras, drive the loop, then shut everything down.
#
# Usage: tools/run_demo.sh <out_dir>
# Afterwards: tools/make_demo_video.sh <out_dir> docs/agv_demo
set -eu
OUT=${1:?usage: tools/run_demo.sh <out_dir>}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT/frames"

export GZ_PARTITION=${GZ_PARTITION:-agvdemo}
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-77}

# headless: no GUI, software or offscreen rendering still fills the cameras
setsid ros2 launch my_agv_description my_warehouse.launch.py headless:=true \
  > "$OUT/launch.log" 2>&1 < /dev/null &
LAUNCH_PGID=$!
cleanup() {
  kill -- -"$LAUNCH_PGID" 2>/dev/null || true
  sleep 2
  fastdds shm clean > /dev/null 2>&1 || true
}
trap cleanup EXIT

echo "waiting for /odom and the demo cameras..."
for _ in $(seq 1 90); do
  if ros2 topic list 2>/dev/null | grep -q "^/odom$"; then break; fi
  sleep 2
done

setsid python3 "$HERE/record_demo.py" --out "$OUT/frames" --every 1 \
  > "$OUT/record.log" 2>&1 < /dev/null &
REC_PGID=$!
sleep 3

python3 -u "$HERE/drive_demo.py" 2>&1 | tee "$OUT/drive.log"

sleep 2
kill -- -"$REC_PGID" 2>/dev/null || true
sleep 3

echo "frames: $(find "$OUT/frames" -name '*.png' | wc -l)"
