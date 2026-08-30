#!/bin/bash

# 配置变量
PROJECT_NAME="iceberg-front"
NGINX_CONF_DEST="/etc/nginx/conf.d/$PROJECT_NAME.conf"
BUILD_PATH=$(pwd)/dist
export DOMAIN="localhost"
export DIST_PATH="/var/www/$PROJECT_NAME"

# Nginx配置
# 1. 确保目录存在
if [ ! -d "/etc/nginx/conf.d" ]; then
    echo "📂 创建 conf.d 目录..."
    sudo mkdir -p /etc/nginx/conf.d
fi

# 2. 确保主配置文件包含了 conf.d
if ! grep -q "include /etc/nginx/conf.d/\*.conf;" /etc/nginx/nginx.conf; then
    echo "🔧 在 nginx.conf 中添加 include 指令..."
    # 使用 sed 在 http 块中插入 include（这步需谨慎，通常默认都有）
    sudo sed -i '/http {/a \    include /etc/nginx/conf.d/*.conf;' /etc/nginx/nginx.conf
fi

echo "🚀 开始构建项目..."
npm install && npm run build

echo "📂 准备静态文件目录..."
sudo mkdir -p $DIST_PATH
sudo cp -r $BUILD_PATH/* $DIST_PATH/

echo "🛠 生成 Nginx 配置..."
# 使用 envsubst 替换模板中的变量，并输出到临时文件
envsubst '$DOMAIN $DIST_PATH' < ./nginx.conf.template > ./$PROJECT_NAME.conf

echo "🔗 应用 Nginx 配置..."
sudo mv ./$PROJECT_NAME.conf $NGINX_CONF_DEST

echo "🔄 检查配置并重启 Nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo "✅ 部署完成！"
