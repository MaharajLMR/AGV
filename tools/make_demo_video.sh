#!/usr/bin/env bash
# Build the README video and GIF from a run of tools/run_demo.sh:
#   title card -> chase camera -> top camera -> link card.
#
# Usage: tools/make_demo_video.sh <run_dir> [out_basename]
set -eu
RUN=${1:?usage: tools/make_demo_video.sh <run_dir> [out_basename]}
OUT=${2:-docs/agv_demo}
TMP=$(mktemp -d)
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
FONT_R=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
W=1280; H=720; FPS=20     # frames are 10 per sim second, so 20 fps is 2x speed
BG=0x101418

mkdir -p "$(dirname "$OUT")"

card() {  # card <out.mp4> <seconds> <title> <subtitle>
  ffmpeg -y -loglevel error -f lavfi -i "color=c=$BG:s=${W}x${H}:d=$2:r=$FPS" -vf "\
drawtext=fontfile=$FONT:text='$3':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=h/2-60,\
drawtext=fontfile=$FONT_R:text='$4':fontcolor=0xc8cdd2:fontsize=28:x=(w-text_w)/2:y=h/2+20" \
    -c:v libx264 -pix_fmt yuv420p "$1"
}

clip() {  # clip <frames_dir> <out.mp4> <caption> <keep every Nth frame>
  ffmpeg -y -loglevel error -framerate $FPS -i "$1/frame_%05d.png" -vf "\
select='not(mod(n\\,$4))',setpts=N/($FPS*TB),\
scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:color=$BG,\
drawtext=fontfile=$FONT:text='$3':fontcolor=white:fontsize=24:box=1:boxcolor=${BG}cc:boxborderw=10:x=w-text_w-22:y=h-text_h-22" \
    -c:v libx264 -pix_fmt yuv420p -r $FPS "$2"
}

card "$TMP/0.mp4" 3 "AGV" "differential drive + 2D lidar, ROS 2 Jazzy and Gazebo Harmonic"
clip "$RUN/frames/chase" "$TMP/1.mp4" "4x speed" 2
clip "$RUN/frames/top"   "$TMP/2.mp4" "top view, 6x speed" 3
card "$TMP/3.mp4" 2 "github.com/MaharajLMR/AGV" ""

for p in 0 1 2 3; do printf "file '%s'\n" "$TMP/$p.mp4"; done > "$TMP/list.txt"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$TMP/list.txt" -c copy "$OUT.mp4"

# README GIF: chase camera only, smaller and fewer colours so it stays under ~5 MB
ffmpeg -y -loglevel error -i "$TMP/1.mp4" \
  -vf "fps=10,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer" \
  "$OUT.gif"

rm -rf "$TMP"
ls -la "$OUT.mp4" "$OUT.gif"
