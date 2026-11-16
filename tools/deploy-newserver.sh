#!/bin/bash
# CodeFlow 官网新机部署（服务器侧脚本）
#
# 前置：本地已把站点产物与以下文件推到服务器 /tmp/upload/
#   site_counter.py、site-counter.service、server.py
#   codeflow.com.cn.pem、codeflow.com.cn.key（DigiCert）
#   站点产物用 rsync 直接同步到 /var/www/testops-site/
#
# 用法：scp -P <ssh端口> tools/deploy-newserver.sh root@host:/tmp/ && ssh -p <端口> root@host 'bash /tmp/deploy-newserver.sh'
set -e
exec > /tmp/deploy.log 2>&1
echo "===== 开始 $(date '+%F %T') ====="

echo "===== 1. dnf 源（CentOS Stream 9 走阿里云 9-stream；默认 metalink 指向的 CDN 在部分线路上不可达会卡住）====="
mkdir -p /etc/yum.repos.d.disabled
mv -f /etc/yum.repos.d/centos.repo /etc/yum.repos.d/centos-addons.repo /etc/yum.repos.d.disabled/ 2>/dev/null || true
cat > /etc/yum.repos.d/aliyun-stream.repo <<'REPO'
[baseos]
name=Aliyun CentOS Stream $releasever - BaseOS
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/BaseOS/$basearch/os/
gpgcheck=0
enabled=1
skip_if_unavailable=1

[appstream]
name=Aliyun CentOS Stream $releasever - AppStream
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/AppStream/$basearch/os/
gpgcheck=0
enabled=1
skip_if_unavailable=1
REPO
cat > /etc/dnf/dnf.conf <<'EOF'
[main]
gpgcheck=0
installonly_limit=3
clean_requirements_on_remove=True
best=True
skip_if_unavailable=True
timeout=15
retries=2
minrate=1000
fastestmirror=0
EOF
dnf clean all >/dev/null 2>&1 || true

echo "===== 2. nginx ====="
dnf install -y nginx
systemctl enable --now nginx
nginx -v

echo "===== 3. 目录与证书 ====="
mkdir -p /var/www/testops-site /opt/site-counter /etc/nginx/ssl /opt/codeflow-app
if [ -f /tmp/upload/codeflow.com.cn.pem ]; then
  cp /tmp/upload/codeflow.com.cn.pem /etc/nginx/ssl/codeflow.com.cn.pem
  cp /tmp/upload/codeflow.com.cn.key /etc/nginx/ssl/codeflow.com.cn.key
  chmod 644 /etc/nginx/ssl/codeflow.com.cn.pem
  chmod 600 /etc/nginx/ssl/codeflow.com.cn.key
  echo "证书已安装"
else
  echo "!! 未找到证书，仅部署 HTTP"
fi

echo "===== 4. nginx 站点配置 ====="
cat > /etc/nginx/conf.d/codeflow.conf <<'NGINX'
# CodeFlow 官网主站（CodeFlow 主品牌 + TestOps 模块）
limit_req_zone $binary_remote_addr zone=pv_limit:10m rate=30r/s;

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name codeflow.com.cn 103.39.64.76;
    root /var/www/testops-site;
    index index.html;

    client_max_body_size 30m;

    # HTML 每次回源校验（避免浏览器缓存旧页面），静态资源长缓存
    add_header Cache-Control "no-cache, must-revalidate" always;
    location ~* \.(css|js|svg|png|jpg|jpeg|gif|webp|woff2?|ttf|ico)$ {
        add_header Cache-Control "public, max-age=604800" always;
    }

    # 浏览量统计（自建计数服务 8905）
    location /api/counter/ {
        proxy_pass http://127.0.0.1:8905/api/;
        proxy_set_header X-Real-IP $remote_addr;
        access_log off;
    }

    # 登录/注册与资源下载（FastAPI 8906）
    location /api/auth/       { proxy_pass http://127.0.0.1:8906; proxy_set_header X-Real-IP $remote_addr; }
    location /api/resources/  { proxy_pass http://127.0.0.1:8906; proxy_set_header X-Real-IP $remote_addr; }
    location = /api/health    { proxy_pass http://127.0.0.1:8906; }

    error_page 404 /404.html;
    location = /404.html {}
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {}
}

# www → 主域（保留 NAT 对外端口）
server {
    listen 80;
    listen [::]:80;
    server_name www.codeflow.com.cn;
    return 301 http://codeflow.com.cn:63028$request_uri;
}
NGINX

if [ -f /etc/nginx/ssl/codeflow.com.cn.pem ]; then
cat > /etc/nginx/conf.d/codeflow-ssl.conf <<'NGINX'
# CodeFlow 官网 HTTPS（DigiCert DV）
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name codeflow.com.cn;

    ssl_certificate     /etc/nginx/ssl/codeflow.com.cn.pem;
    ssl_certificate_key /etc/nginx/ssl/codeflow.com.cn.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    root /var/www/testops-site;
    index index.html;
    client_max_body_size 30m;

    add_header Cache-Control "no-cache, must-revalidate" always;
    location ~* \.(css|js|svg|png|jpg|jpeg|gif|webp|woff2?|ttf|ico)$ {
        add_header Cache-Control "public, max-age=604800" always;
    }

    location /api/counter/ {
        proxy_pass http://127.0.0.1:8905/api/;
        proxy_set_header X-Real-IP $remote_addr;
        access_log off;
    }
    location /api/auth/       { proxy_pass http://127.0.0.1:8906; proxy_set_header X-Real-IP $remote_addr; }
    location /api/resources/  { proxy_pass http://127.0.0.1:8906; proxy_set_header X-Real-IP $remote_addr; }
    location = /api/health    { proxy_pass http://127.0.0.1:8906; }

    error_page 404 /404.html;
    location = /404.html {}
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {}
}

# www → 主域（443 直连）
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name www.codeflow.com.cn;
    ssl_certificate     /etc/nginx/ssl/codeflow.com.cn.pem;
    ssl_certificate_key /etc/nginx/ssl/codeflow.com.cn.key;
    return 301 https://codeflow.com.cn$request_uri;
}
NGINX
fi

echo "===== 5. SELinux ====="
setsebool -P httpd_can_network_connect 1 2>/dev/null || true
restorecon -Rv /var/www >/dev/null 2>&1 || true

echo "===== 6. 计数服务（纯 stdlib + SQLite）====="
cp /tmp/upload/site_counter.py /opt/site-counter/site_counter.py
cp /tmp/upload/site-counter.service /etc/systemd/system/site-counter.service
PY=$(command -v python3)
sed -i "s|ExecStart=.*|ExecStart=$PY /opt/site-counter/site_counter.py|" /etc/systemd/system/site-counter.service
systemctl daemon-reload
systemctl enable --now site-counter
sleep 2
systemctl is-active site-counter

echo "===== 7. 认证后端（FastAPI 8906）====="
if [ -f /tmp/upload/server.py ]; then
  cp /tmp/upload/server.py /opt/codeflow-app/server.py
  ln -sfn /var/www/testops-site /opt/codeflow-app/site
  mkdir -p /root/.config/pip
  cat > /root/.config/pip/pip.conf <<'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
timeout = 30
EOF
  python3 -m venv /opt/codeflow-app/.venv 2>/dev/null || true
  /opt/codeflow-app/.venv/bin/pip install -q --upgrade pip 2>&1 | tail -1
  /opt/codeflow-app/.venv/bin/pip install -q fastapi uvicorn 2>&1 | tail -3
  /opt/codeflow-app/.venv/bin/python -m py_compile /opt/codeflow-app/server.py && echo "后端编译通过"
  if [ ! -f /opt/codeflow-app/.env ]; then
    cat > /opt/codeflow-app/.env <<'EOF'
# 站点后端运行配置（不含真实密钥）
# 短信：填入阿里云号码认证服务(DYPNS)凭据后才可真正发码
DYPNS_ACCESS_KEY_ID=
DYPNS_ACCESS_KEY_SECRET=
DYPNS_SIGN_NAME=恒创联众
DYPNS_TEMPLATE_CODE=100001
DYPNS_TEMPLATE_PARAM_EXTRA={"min":"5"}
AUTH_DB_PATH=/opt/codeflow-app/auth.db
EOF
    chmod 600 /opt/codeflow-app/.env
  fi
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
  sleep 4
  systemctl is-active codeflow-site
else
  echo "!! 未找到 server.py，跳过后端"
fi

echo "===== 8. 启动 nginx ====="
nginx -t
systemctl reload nginx 2>/dev/null || systemctl restart nginx

echo "===== 9. 自检 ====="
sleep 1
curl -s -o /dev/null -w "首页        %{http_code}\n" http://127.0.0.1/
curl -s -o /dev/null -w "案例集      %{http_code}\n" http://127.0.0.1/cases.html
curl -s -o /dev/null -w "计数器接口  %{http_code}\n" "http://127.0.0.1/api/counter/hit?path=/deploy-check"
curl -s -o /dev/null -w "验证码接口  %{http_code}\n" http://127.0.0.1/api/auth/captcha
systemctl is-active nginx site-counter codeflow-site 2>/dev/null
echo "===== 完成 $(date '+%F %T') ====="
