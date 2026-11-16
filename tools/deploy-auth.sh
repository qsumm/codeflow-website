#!/bin/bash
# CodeFlow 官网后端部署（认证/资源下载）—— 不改任何业务代码，只做运维编排
set -e
APP=/opt/codeflow-app
cd "$APP"

echo "===== 1. 虚拟环境 + 依赖 ====="
# 国内线路 pypi.org 往往不可达，走阿里云 PyPI 镜像
mkdir -p /root/.config/pip
cat > /root/.config/pip/pip.conf <<'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
timeout = 30
EOF
python3 -m venv .venv 2>/dev/null || true
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q fastapi uvicorn
./.venv/bin/python -c "import fastapi, uvicorn; print('fastapi', fastapi.__version__, '| uvicorn', uvicorn.__version__)"

echo "===== 2. 语法检查（Python 3.9 兼容性）====="
./.venv/bin/python -m py_compile server.py && echo "编译通过"

echo "===== 3. .env（无短信凭据，发码会如实报错）====="
if [ ! -f .env ]; then
cat > .env <<'EOF'
# 站点后端运行配置（不含真实密钥）
# 短信：填入阿里云号码认证服务(DYPNS)凭据后才可真正发码
DYPNS_ACCESS_KEY_ID=
DYPNS_ACCESS_KEY_SECRET=
DYPNS_SIGN_NAME=恒创联众
DYPNS_TEMPLATE_CODE=100001
DYPNS_TEMPLATE_PARAM_EXTRA={"min":"5"}
AUTH_DB_PATH=/opt/codeflow-app/auth.db
EOF
chmod 600 .env
echo "已生成 .env"
else
echo ".env 已存在，跳过"
fi

echo "===== 4. systemd 服务 ====="
cat > /etc/systemd/system/codeflow-site.service <<'EOF'
[Unit]
Description=CodeFlow website backend (auth/resources)
After=network.target

[Service]
WorkingDirectory=/opt/codeflow-app
ExecStart=/opt/codeflow-app/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8906
Restart=always
RestartSec=5
MemoryMax=256M

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable codeflow-site >/dev/null 2>&1
systemctl restart codeflow-site
sleep 3
systemctl is-active codeflow-site

echo "===== 5. nginx 反代 API（保留原 /api/counter/）====="
# 主站配置里已经写了 /api/auth/ 等 location 时不要重复建文件（重复 location 会让 nginx -t 失败）
if grep -q "/api/auth/" /etc/nginx/conf.d/codeflow.conf 2>/dev/null; then
  echo "codeflow.conf 已含 API 反代，跳过"
else
  cat > /etc/nginx/conf.d/codeflow-api.conf <<'EOF'
# 认证与资源接口 → FastAPI(8906)；计数器仍走 8905
location /api/auth/      { proxy_pass http://127.0.0.1:8906; proxy_set_header X-Real-IP $remote_addr; }
location /api/resources/ { proxy_pass http://127.0.0.1:8906; proxy_set_header X-Real-IP $remote_addr; }
location = /api/health   { proxy_pass http://127.0.0.1:8906; }
EOF
  sed -i 's#include /etc/nginx/conf.d/\*\.conf;#include /etc/nginx/conf.d/*.conf;#' /etc/nginx/nginx.conf || true
fi
nginx -t 2>&1 | tail -1
systemctl reload nginx

echo "===== 6. 自检 ====="
sleep 1
echo -n "直连后端 captcha: "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8906/api/auth/captcha
echo -n "经 nginx captcha: "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/api/auth/captcha
echo -n "me(未登录):      "; curl -s http://127.0.0.1/api/auth/me | head -c 120; echo
echo -n "计数器(保持):    "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/api/counter/hit?path=/deploy-check
echo "DEPLOY_DONE"
