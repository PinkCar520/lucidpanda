# AlphaSignal SSL 部署说明

## 方案一：使用Let's Encrypt自动获取证书（推荐）

1. 确保域名已解析到服务器IP
2. 在服务器上运行以下命令替换域名：
   ```bash
   sed -i 's/your-domain.com/nocafe.ltd/g' nginx-ssl.conf
   ```
3. 运行部署脚本：
   ```bash
   chmod +x deploy-ssl-guide.sh
   ./deploy-ssl-guide.sh
   ```

## 方案二：使用腾讯云SSL证书

### 步骤1：在腾讯云申请SSL证书
1. 登录腾讯云控制台
2. 进入SSL证书管理
3. 申请免费DV证书
4. 选择DNS验证方式
5. 按照提示添加DNS记录
6. 下载Nginx版本证书

### 步骤2：上传证书到服务器
```bash
# 创建证书目录
mkdir -p ssl-certs

# 上传证书文件（假设下载的证书文件名为 cert.zip）
# 解压后通常包含：
# - 1_nocafe_ltd_bundle.crt (证书文件)
# - 2_nocafe_ltd.key (私钥文件)

# 重命名并放置到正确位置
mv 1_nocafe_ltd_bundle.crt ssl-certs/fullchain.pem
mv 2_nocafe_ltd.key ssl-certs/privkey.pem
```

### 步骤3：更新Nginx配置
编辑 `nginx-ssl.conf` 文件，将证书路径更新为：
```nginx
ssl_certificate /etc/letsencrypt/live/ssl-certs/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/ssl-certs/privkey.pem;
```

或者直接修改为：
```nginx
ssl_certificate /etc/letsencrypt/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/privkey.pem;
```

### 步骤4：启动服务
```bash
# 启动带SSL的AlphaSignal服务（现在在原docker-compose.yml中）
sudo docker-compose up -d
```

## 方案三：使用Caddy服务器（最简单）

如果以上方案仍有问题，可以使用Caddy自动获取证书：

1. 安装Caddy：
```bash
# 在服务器上执行
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

2. 创建Caddyfile：
```bash
nocafe.ltd {
    reverse_proxy api:8001
}
```

3. 启动Caddy：
```bash
sudo caddy run --config /path/to/Caddyfile
```

## iOS应用配置更新

无论使用哪种方案，都需要更新iOS应用配置：

编辑 `/mobile/ios/Packages/AlphaCore/Sources/AlphaCore/Network/APIClient.swift`：

```swift
#if DEBUG
private let baseURL = URL(string: "https://nocafe.ltd")!  // 使用HTTPS
#else
private let baseURL = URL(string: "https://nocafe.ltd")!
#endif
```

## 验证部署

1. 检查Docker服务状态：
```bash
sudo docker-compose ps
```

2. 检查SSL证书：
```bash
openssl s_client -connect nocafe.ltd:443 -servername nocafe.ltd
```

3. 测试API访问：
```bash
curl -k https://nocafe.ltd/api/health
```

## 故障排除

如果遇到问题，请检查：

1. 域名解析是否正确
2. 防火墙是否开放80和443端口
3. Docker服务是否正常运行
4. 证书文件路径是否正确