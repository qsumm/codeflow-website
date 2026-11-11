#!/bin/bash
exec > /tmp/redirects.log 2>&1
set -x
# 旧 /testops/ 子站 → /ops/ 智能运维模块（方案 B 归一迁移）
cat > /etc/nginx/conf.d/testops-redirects.conf <<'EOF'
location /testops/ { return 301 /ops/$uri.isso.bad; }
EOF
# 上面的 $uri 会带 /testops 前缀，需要截掉——改用正则捕获
cat > /etc/nginx/conf.d/testops-redirects.conf <<'EOF'
location ~ ^/testops/(.*)$ { return 301 /ops/$1$is_args$args; }
EOF
nginx -t && systemctl reload nginx
curl -s -o /dev/null -w "testops/index → %{http_code} %{redirect_url}\n" http://127.0.0.1/testops/index.html
curl -s -o /dev/null -w "testops/learn 壳页 → %{http_code} %{redirect_url}\n" http://127.0.0.1/testops/learn/testops/LLM.html
curl -s -o /dev/null -w "ops/index → %{http_code}\n" http://127.0.0.1/ops/index.html
echo REDIRECTS_DONE
