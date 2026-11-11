#!/bin/bash
# CodeFlow 官网新机部署：nginx + 站点 + 计数服务（迁移含数据）
set -x
exec > /tmp/deploy.log 2>&1

echo "===== 1. nginx ====="
dnf install -y nginx && nginx -v

echo "===== 2. 目录 ====="
mkdir -p /var/www /opt/site-counter

echo "===== 3. nginx 配置 ====="
cat > /etc/nginx/conf.d/codeflow.conf <<'NGINX'
# CodeFlow 官网（含 TestOps 子站）
limit_req_zone $binary_remote_addr zone=pv_limit:10m rate=30r/s;

server {
    listen 80;
    listen [::]:80;
    server_name _;
    root /var/www/testops-site;

    client_max_body_size 30m;

    # 缓存策略：HTML/文档回源校验，静态资源 7 天
    add_header Cache-Control "no-cache, must-revalidate" always;
    location ~* \.(css|js|svg|png|jpg|jpeg|gif|webp|woff2?|ttf|ico)$ {
        add_header Cache-Control "public, max-age=604800" always;
    }

    # 浏览量统计：自建计数服务
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
nginx -t

echo "===== 4. SELinux（nginx 读写目录权限）====="
getenforce
restorecon -Rv /var/www 2>/dev/null || true
setsebool -P httpd_can_network_connect 1 2>/dev/null || true

echo "===== 5. 计数服务 ====="
cp /tmp/upload/site_counter.py /opt/site-counter/site_counter.py
cp /tmp/upload/site-counter.service /etc/systemd/system/site-counter.service
sed -i 's|python3.11|python3.9|' /etc/systemd/system/site-counter.service 2>/dev/null
systemctl daemon-reload
systemctl enable --now site-counter

echo "===== 6. 启动 ====="
systemctl enable --now nginx
nginx -s reload 2>/dev/null || systemctl restart nginx

echo "===== 7. 本机自检 ====="
sleep 2
curl -s -o /dev/null -w "首页 %{http_code}\n" http://127.0.0.1/
curl -s http://127.0.0.1:8905/api/hit?path=/deploy-check && echo
curl -s "http://127.0.0.1/api/counter/hit?path=/deploy-check" && echo
nginx -v 2>&1
echo "DEPLOY_SCRIPT_DONE"
