# AlphaSignal 账号系统技术实现方案

## 1. 架构设计概览

为了同时支持 Web (Next.js) 和未来的 Mobile App (iOS SwiftUI)，我们将采用 **前后端分离的 JWT (JSON Web Token) 认证架构**。

- **核心原则**：Python 后端作为唯一的“认证中心 (Identity Provider)”。
- **通信方式**：所有客户端（Web, iOS）通过 REST API 进行登录、注册和令牌刷新。
- **状态管理**：无状态认证 (Stateless)，服务器不存储 Session，仅验证签名。

```mermaid
graph TD
    User[用户] -->|1. 注册/登录| Web[Next.js Web]
    User -->|1. 注册/登录| iOS[iOS App]
    
    Web -->|2. POST /api/auth/login| API[Python FastAPI]
    iOS -->|2. POST /api/auth/login| API
    
    API -->|3. 验证凭据| DB[(PostgreSQL)]
    API -->|4. 返回 JWT (Access + Refresh)| Web
    API -->|4. 返回 JWT (Access + Refresh)| iOS
    
    Web -->|5. 请求携带 Bearer Token| API
    iOS -->|5. 请求携带 Bearer Token| API
```

---

## 2. 数据库设计 (PostgreSQL)

需要在现有的 `alphasignal_core` 数据库中新增用户相关表。

### 2.1 新增 `users` 表
存储用户的核心身份信息。

```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 使用 UUID 防止遍历
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(50),
    role VARCHAR(20) DEFAULT 'user', -- 'user', 'admin', 'pro'
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
```

### 2.2 修改 `fund_watchlist` 表
将原有的 `user_id` (TEXT) 迁移为关联 `users` 表的外键。

```sql
-- 1. 临时重命名旧列
ALTER TABLE fund_watchlist RENAME COLUMN user_id TO old_user_id;

-- 2. 添加新列 (允许为空，因为可能有历史数据或未登录数据)
ALTER TABLE fund_watchlist ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- 3. (可选) 数据迁移策略：
-- 如果 old_user_id 是 'default'，可以创建一个默认系统用户并关联
-- 或者在应用层处理，未登录用户存在本地 Storage，登录后同步到服务端

-- 4. 建立新索引
CREATE INDEX idx_watchlist_user ON fund_watchlist(user_id);
```

---

## 3. 后端实现 (Python/FastAPI)

### 3.1 新增依赖
在 `requirements.txt` 中添加：
```text
python-jose[cryptography]  # JWT 处理
passlib[bcrypt]            # 密码哈希
python-multipart           # OAuth2 表单处理
email-validator            # Pydantic 邮箱验证
```

### 3.2 目录结构规划
建议在 `src/alphasignal` 下新增 `auth` 模块：

```text
src/alphasignal/
├── auth/
│   ├── __init__.py
│   ├── models.py       # Pydantic 模型 (UserCreate, Token, etc.)
│   ├── security.py     # 密码 Hash, JWT 生成/解码
│   ├── router.py       # FastAPI 路由 (/login, /register)
│   └── dependencies.py # get_current_user 依赖注入
```

### 3.3 核心逻辑伪代码

**A. 密码处理 (`security.py`)**
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)
```

**B. 依赖注入 (`dependencies.py`)**
```python
async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    payload = decode_jwt(token)
    user = db.get_user(payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
```

**C. 路由接口**
- `POST /api/auth/register`: 接受 email/password，创建用户。
- `POST /api/auth/login`: 校验密码，返回 Access Token (有效期 30分钟) 和 Refresh Token (有效期 7-30天)。
- `POST /api/auth/refresh`: 使用 Refresh Token 获取新的 Access Token。
- `GET /api/users/me`: 获取当前用户信息 (需鉴权)。

---

## 4. Web 端集成 (Next.js)

### 4.1 认证状态管理
不建议使用复杂的 `next-auth` (因为它更偏向于全栈 SSR 方案，且配置复杂)，建议使用轻量级的 **Context + Hook** 方案，更容易对接纯后端 API。

**文件：`web/context/AuthContext.tsx`**
```typescript
interface AuthContextType {
  user: User | null;
  login: (credentials) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}
```

### 4.2 存储策略
- **Access Token**: 存储在内存中 (React State) 或 `Cookie` (推荐)。
- **Refresh Token**: 存储在 `HttpOnly Cookie` 中（最安全，防 XSS）或 `localStorage`（实现简单，适合初期，Web/iOS 统一）。
  - *建议初期方案*：统一存 `localStorage`，后续针对 Web 优化为 Cookie。

### 4.3 中间件保护
在 `web/middleware.ts` 中拦截受保护路由（如 `/dashboard`, `/settings`），检查是否存在 Token。

---

## 5. iOS (SwiftUI) 集成预案

iOS 端不需要重新设计，直接调用上述 Python API。

### 5.1 存储
使用 **Keychain Services** 安全存储 `accessToken` 和 `refreshToken`。
*推荐库*: `KeychainAccess` 或 `Valet`。

### 5.2 网络层 (Network Layer)
实现一个 `NetworkManager`，具备拦截器功能：
1. 发送请求前：自动添加 `Authorization: Bearer <token>` 头。
2. 收到 401 Unauthorized 后：
   - 暂停原请求。
   - 调用 `/api/auth/refresh` 刷新 Token。
   - 刷新成功：重试原请求。
   - 刷新失败：跳转至登录页。

### 5.3 数据同步
- **自选股同步**：App 启动时，调用 `GET /api/watchlist` 拉取最新数据，与本地 CoreData 比较，实现双向同步。

---

## 6. 实施路线图 (Roadmap)

### Phase 1: 基础设施 (预计 1-2 天)
- [ ] 安装 Python 依赖库。
- [ ] 执行数据库迁移 (创建 `users` 表，修改 `watchlist` 表)。
- [ ] 实现 `src/alphasignal/auth` 后端模块（哈希、JWT 工具）。

### Phase 2: API 开发 (预计 2-3 天)
- [ ] 开发注册、登录接口。
- [ ] 修改 `add_to_watchlist` 等现有接口，支持从 `request.state.user` 获取 `user_id`。
- [ ] 使用 FastAPI `Depends` 保护敏感接口。

### Phase 3: 前端对接 (预计 3-4 天)
- [ ] Next.js 增加登录/注册页面 UI。
- [ ] 实现 `useAuth` Hook 和 Token 管理。
- [ ] 对接后端登录接口，实现自选股数据跟随账号展示。
