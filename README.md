# DarkForest

匿名聊天应用 — 口令即入，阅后即焚。

## 功能特性

- **匿名聊天**：通过口令创建或加入聊天空间，无需注册
- **实时通信**：基于 WebSocket 的实时消息推送
- **自动销毁**：无活动超时后空间自动销毁，消息暂存后定时清除
- **风控系统**：IP 级限流，创建/加入/发送频率均可动态配置
- **管理后台**：仪表盘、空间管理、系统配置、用户管理
- **响应式设计**：适配手机与桌面端，支持深色/亮色主题切换

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL |
| 前端 | React 19 + TypeScript + Vite + shadcn/ui + TailwindCSS |
| 实时 | WebSocket (FastAPI 原生) |
| 部署 | Docker Compose + Nginx |
| CI/CD | GitHub Actions |

## 项目结构

```
DarkForest/
├── backend/
│   ├── app/
│   │   ├── api/            # API 路由 (auth, rooms, admin, websocket)
│   │   ├── models/         # SQLAlchemy 数据模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── services/       # 业务逻辑
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库连接
│   │   └── main.py         # 应用入口
│   ├── alembic/            # 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/ui/  # shadcn/ui 组件
│   │   ├── hooks/          # 自定义 hooks
│   │   ├── pages/          # 页面组件
│   │   └── types/          # TypeScript 类型
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   └── default.conf
├── .github/workflows/
│   └── ci.yml
└── docker-compose.yml
```

## 快速开始

### Docker Compose (推荐)

```bash
git clone https://github.com/your-repo/DarkForest.git
cd DarkForest

# 修改配置
cp backend/.env.example backend/.env
# 编辑 .env 设置 JWT 密钥和管理员密码

# 启动
docker compose up -d

# 访问 http://localhost
# 管理后台 http://localhost/admin/login
```

### 本地开发

**后端：**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端：**

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

## 默认管理员账户

| 字段 | 值 |
|------|-----|
| 用户名 | admin |
| 密码 | admin123456 |

**生产环境请务必修改密码和 JWT 密钥！**

## 系统配置

管理员可在后台动态修改以下配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| room_timeout_minutes | 10 | 无活动自动销毁时间（分钟） |
| message_retention_hours | 24 | 消息保留时间（小时） |
| max_rooms_per_hour | 5 | 每 IP 每小时最多创建空间数 |
| max_joins_per_hour | 10 | 每 IP 每小时最多加入空间数 |
| max_messages_per_minute | 30 | 每 IP 每分钟最多发送消息数 |

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/register | 用户注册 |
| POST | /api/rooms | 创建聊天空间 |
| POST | /api/rooms/join | 加入聊天空间 |
| GET | /api/rooms | 列出活跃空间 |
| WS | /ws/{room_id} | WebSocket 连接 |
| GET | /api/admin/stats | 系统统计 |
| POST | /api/admin/rooms/{id}/destroy | 销毁空间 |
| GET | /api/admin/configs | 系统配置 |
| PUT | /api/admin/configs/{key} | 更新配置 |

## License

MIT
