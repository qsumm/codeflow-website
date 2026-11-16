#!/bin/bash
# 等待 SSH 解封 → 自动部署（站点 + 后端）
cd /Users/summer/aiops-website || exit 1
for i in $(seq 1 40); do
  if timeout 25 ssh -o BatchMode=yes -o ConnectTimeout=15 codeflow-new "echo SSH_OK" 2>/dev/null | grep -q SSH_OK; then
    echo "[$(date +%H:%M:%S)] SSH 恢复（第 $i 次尝试）"
    break
  fi
  echo "[$(date +%H:%M:%S)] 第 $i 次仍被封，等待 3 分钟"
  sleep 180
done

if ! timeout 25 ssh -o BatchMode=yes -o ConnectTimeout=15 codeflow-new "echo SSH_OK" 2>/dev/null | grep -q SSH_OK; then
  echo "RESULT: SSH 长时间未恢复，需在面板重启或联系服务商"
  exit 1
fi

echo "===== 1. 同步站点 ====="
rsync -az --delete -e "ssh -o BatchMode=yes" site/ codeflow-new:/var/www/testops-site/ && echo "站点已同步"

echo "===== 2. 上传后端 ====="
ssh -o BatchMode=yes codeflow-new "mkdir -p /opt/codeflow-app && ln -sfn /var/www/testops-site /opt/codeflow-app/site"
ssh -o BatchMode=yes codeflow-new "cat > /opt/codeflow-app/server.py" < server.py
ssh -o BatchMode=yes codeflow-new "cat > /tmp/deploy-auth.sh" < tools/deploy-auth.sh
echo "后端已上传"

echo "===== 3. 执行后端部署 ====="
timeout 400 ssh -o BatchMode=yes codeflow-new "bash /tmp/deploy-auth.sh" 2>&1 | tail -20

echo "===== 4. 线上验证 ====="
curl -s -o /dev/null -m 15 -w "首页 %{http_code}\n" http://103.39.64.76:63028/
curl -s -o /dev/null -m 15 -w "验证码接口 %{http_code}\n" http://103.39.64.76:63028/api/auth/captcha
curl -s -m 15 http://103.39.64.76:63028/api/auth/me | head -c 120; echo
echo "PIPELINE_DONE"
