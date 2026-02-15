#!/bin/bash

echo "开始部署 AlphaSignal with SSL..."

DOMAIN="your-domain.com"  # 请替换为您的实际域名
EMAIL="your-email@example.com"  # 请替换为您的邮箱

echo "第一步：停止现有的Docker服务..."
sudo docker-compose down

echo "第二步：创建必要的目录..."
mkdir -p ssl-certs nginx-logs

echo "第三步：创建临时Nginx配置用于证书验证..."
sudo mkdir -p /var/www/certbot
sudo chown -R $USER:$USER /var/www/certbot

# 创建临时配置
cat > temp-nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name your-domain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 404;
        }
    }
}
EOF

# 启动临时Nginx
docker run -d --name temp-nginx \
  -p 80:80 \
  -v $(pwd)/temp-nginx.conf:/etc/nginx/nginx.conf \
  -v /var/www/certbot:/var/www/certbot \
  nginx:alpine

echo "等待Nginx启动..."
sleep 5

echo "第四步：获取SSL证书..."
if ! command -v certbot &> /dev/null; then
    echo "安装Certbot..."
    sudo apt update
    sudo apt install -y certbot
fi

# 获取证书
sudo certbot certonly --webroot \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email \
  --webroot-path=/var/www/certbot \
  -d $DOMAIN

if [ $? -eq 0 ]; then
    echo "SSL证书获取成功！"
    
    # 复制证书到项目目录
    sudo cp -r /etc/letsencrypt/live/$DOMAIN/* ssl-certs/
    sudo cp -r /etc/letsencrypt/archive/$DOMAIN/* ssl-certs/
    sudo chown -R $USER:$USER ssl-certs/
    
    # 更新Nginx配置中的域名
    sed -i "s/your-domain.com/$DOMAIN/g" nginx-ssl.conf
    
    echo "第五步：停止临时Nginx..."
    docker stop temp-nginx
    docker rm temp-nginx
    
    echo "第六步：启动带SSL的AlphaSignal服务..."
    sudo docker-compose -f docker-compose-ssl.yml up -d
    
    echo "部署完成！"
    echo "请确保在DNS中将 $DOMAIN 指向您的服务器IP"
    echo "服务将在 https://$DOMAIN 可用"
else
    echo "SSL证书获取失败，请检查："
    echo "1. 域名是否正确解析到此服务器"
    echo "2. 80端口是否开放"
    echo "3. 防火墙设置"
    
    docker stop temp-nginx
    docker rm temp-nginx
fi