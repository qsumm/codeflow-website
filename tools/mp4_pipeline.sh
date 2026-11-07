#!/bin/bash
# mp4 传输管线：GitHub 大文件通道当前全部不稳，循环重试直到成功，成功后自动走完整交付流程
cd /Users/summer/aiops-website || exit 1
EXPECTED=8577914
URL="repos/BPCKeeeeeepOn/codeflow-website/contents/site/assets/media/codeflow-product-demo.mp4?ref=feature/homepage-video"
TMP=/tmp/cfmp4.bin
LOG=/tmp/cfmp4.log
: > "$LOG"

for i in $(seq 1 12); do
  echo "[$(date +%H:%M:%S)] 尝试 $i (raw)" >> "$LOG"
  timeout 580 gh api -H "Accept: application/vnd.github.raw" "$URL" > "$TMP" 2>>"$LOG"
  S=$(stat -f%z "$TMP" 2>/dev/null || echo 0)
  echo "[$(date +%H:%M:%S)] raw: $S bytes" >> "$LOG"
  if [ "$S" = "$EXPECTED" ]; then break; fi
  # 隔轮换 blob API 通道
  echo "[$(date +%H:%M:%S)] 尝试 $i-b (blob)" >> "$LOG"
  SHA=$(timeout 60 gh api "repos/BPCKeeeeeepOn/codeflow-website/contents/site/assets/media/codeflow-product-demo.mp4?ref=feature/homepage-video" --jq .sha 2>>"$LOG")
  if [ -n "$SHA" ]; then
    timeout 580 gh api "repos/BPCKeeeeeepOn/codeflow-website/git/blobs/$SHA" 2>>"$LOG" | python3 -c "import sys,json,base64; d=json.load(sys.stdin); sys.stdout.buffer.write(base64.b64decode(d['content']))" > "$TMP" 2>>"$LOG"
    S=$(stat -f%z "$TMP" 2>/dev/null || echo 0)
    echo "[$(date +%H:%M:%S)] blob: $S bytes" >> "$LOG"
    [ "$S" = "$EXPECTED" ] && break
  fi
  sleep 30
done

if [ "$S" != "$EXPECTED" ]; then echo "RESULT: mp4 传输最终失败" >> "$LOG"; exit 1; fi
echo "RESULT: mp4 到手 $S bytes" >> "$LOG"
cp "$TMP" site/assets/media/codeflow-product-demo.mp4 || exit 1

echo "== 构建+守卫 ==" >> "$LOG"
python3 tools/build_pages.py >/dev/null 2>&1
python3 tools/build_pages.py --check >> "$LOG" 2>&1 || { echo "RESULT: --check 失败" >> "$LOG"; exit 1; }
python3 tools/check_all.py >> "$LOG" 2>&1 || { echo "RESULT: 守卫失败" >> "$LOG"; exit 1; }

echo "== 提交 ==" >> "$LOG"
git add -A
git commit -q -m "合并 feature/homepage-video：首页新增产品演示视频（同事 BPCKeeeeeepOn 的工作，经 fork 拉回）

- 视频区块：封面预览 + 弹层播放（preload=none 点击才加载，8.6MB mp4）
- 新增 product-demo.css/js 与媒体资产；来源 fork BPCKeeeeeepOn/codeflow-website" >> "$LOG" 2>&1 || echo "(无变更可提交)" >> "$LOG"

echo "== 部署 ==" >> "$LOG"
rsync -az --delete -e "ssh -S /tmp/evd.sock -o BatchMode=yes" site/ target-1.15.66.59:/var/www/testops-site/ >> "$LOG" 2>&1

echo "== 推送 GitHub ==" >> "$LOG"
PUSHED=0
for i in $(seq 1 8); do
  if git push -q origin main 2>>"$LOG"; then PUSHED=1; echo "PUSH_OK (第 $i 次尝试)" >> "$LOG"; break; fi
  sleep 20
done
[ "$PUSHED" = "1" ] || echo "WARN: push 未成功，稍后需手动 git push" >> "$LOG"

echo "== 线上验证 ==" >> "$LOG"
curl -s -o /dev/null -w "首页 %{http_code}\n" http://1.15.66.59/ >> "$LOG"
curl -s -o /dev/null -w "mp4 %{http_code} %{size_download}B\n" --max-time 60 http://1.15.66.59/assets/media/codeflow-product-demo.mp4 >> "$LOG"
echo "PIPELINE_DONE" >> "$LOG"
