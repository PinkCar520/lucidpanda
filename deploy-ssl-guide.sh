#!/bin/bash

echo "=== AlphaSignal SSL 部署向导 ==="
echo ""
echo "在继续之前，请确保："
echo "1. 域名 nocafe.ltd 已解析到此服务器的IP"
echo "2. 服务器的80和443端口已开放"
echo ""

DOMAIN="nocafe.ltd"
read -p "请输入您的邮箱地址: " EMAIL

echo ""
echo "您输入的信息："
echo "域名: nocafe.ltd"
echo "邮箱: $EMAIL"
echo ""
read -p "确认无误？(y/N): " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "操作已取消"
    exit 1
fi

echo ""
echo "开始部署过程..."

# 停止现有服务
echo "停止现有Docker服务..."
sudo docker-compose down 2>/dev/null || true

# 创建必要目录
echo "创建必要目录..."
mkdir -p ssl-certs nginx-logs

# 检查Certbot是否安装
if ! command -v certbot &> /dev/null; then
    echo "安装Certbot..."
    sudo apt update
    sudo apt install -y certbot
fi

# 创建临时web目录
sudo mkdir -p /var/www/certbot

echo "尝试获取SSL证书..."
sudo certbot certonly --webroot \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email \
  --webroot-path=/var/www/certbot \
  -d nocafe.ltd

if [ $? -eq 0 ]; then
    echo "✅ SSL证书获取成功！"
    
    # 复制证书到项目目录
    sudo cp -r /etc/letsencrypt/live/nocafe.ltd/* ssl-certs/ 2>/dev/null || true
    sudo cp -r /etc/letsencrypt/archive/nocafe.ltd/* ssl-certs/ 2>/dev/null || true
    sudo chown -R $USER:$USER ssl-certs/ 2>/dev/null || true
    
    # 更新配置文件中的域名
    sed -i "s/your-domain.com/nocafe.ltd/g" nginx-ssl.conf
    
    echo "启动带SSL的AlphaSignal服务..."
    sudo docker-compose up -d

    echo ""
    echo "🎉 部署完成！"
    echo "您的服务将在 https://nocafe.ltd 可用"
    echo ""
    echo "iOS应用配置更新："
    echo "修改 /mobile/ios/Packages/AlphaCore/Sources/AlphaCore/Network/APIClient.swift"
    echo "将 baseURL 改为: \"https://nocafe.ltd\""
    echo ""
    echo "检查服务状态："
    echo "sudo docker-compose ps"
else
    echo "❌ SSL证书获取失败"
    echo "请检查："
    echo "1. 域名 nocafe.ltd 是否正确解析到此服务器"
    echo "2. 80端口是否开放"
    echo "3. 防火墙设置"
    echo ""
    echo "您也可以尝试使用腾讯云控制台申请SSL证书，然后手动配置"
fi