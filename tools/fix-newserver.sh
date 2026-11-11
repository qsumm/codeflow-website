#!/bin/bash
set -x
exec > /tmp/fix.log 2>&1

echo "===== A. 计数服务 python 路径 ====="
PY=$(command -v python3); echo "python3 = $PY"
sed -i "s|ExecStart=.*|ExecStart=$PY /opt/site-counter/site_counter.py|" /etc/systemd/system/site-counter.service
grep ExecStart /etc/systemd/system/site-counter.service
systemctl daemon-reload && systemctl restart site-counter
sleep 2; systemctl is-active site-counter
curl -s http://127.0.0.1:8905/api/stats && echo

echo "===== B. 仓库文件改阿里云 ====="
cat /etc/yum.repos.d/centos.repo | head -12
rm -f /etc/yum.repos.d/*.repo
cat > /etc/yum.repos.d/aliyun.repo <<'REPO'
[baseos]
name=CentOS Stream 9 - BaseOS
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/BaseOS/x86_64/os/
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/centos-stream/RPM-GPG-KEY-CentOS-Official-Simplified
enabled=1

[appstream]
name=CentOS Stream 9 - AppStream
baseurl=https://mirrors.aliyun.com/centos-stream/9-stream/AppStream/x86_64/os/
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/centos-stream/RPM-GPG-KEY-CentOS-Official-Simplified
enabled=1
REPO
dnf clean all >/dev/null 2>&1
timeout 200 dnf makecache 2>&1 | tail -2

echo "===== C. 装 nginx ====="
dnf install -y nginx 2>&1 | tail -3
nginx -v 2>&1

echo "===== D. 配置 + 启动 ====="
mkdir -p /var/www
cat > /etc/nginx/conf.d/codeflow.conf <<'NGINX'
limit_req_zone $binary_remote_addr zone=pv_limit:10m rate=30r/s;
server {
    listen 80;
    listen [::]:80;
    server_name _;
    root /var/www/testops-site;
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
    error_page 404 /404.html;
    location = /404.html {}
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {}
}
NGINX
nginx -t && systemctl enable --now nginx && systemctl restart nginx

echo "===== E. 自检 ====="
sleep 2
curl -s -o /dev/null -w "nginx:80 → %{http_code}（404 因为还没放文件）\n" http://127.0.0.1/
systemctl is-active nginx site-counter
echo "FIX_DONE"
