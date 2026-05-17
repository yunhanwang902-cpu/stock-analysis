# ProTrade 股票分析系统 — 后端架构设计

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              客户端层                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │  Web 前端   │  │  移动端 App │  │  第三方 API │                     │
│  │  (React)    │  │  (Flutter)  │  │  消费者     │                     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                     │
└─────────┼────────────────┼────────────────┼─────────────────────────────┘
          │                │                │
          └────────────────┴────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Nginx     │  ← SSL/TLS, 静态资源, 反向代理
                    │   (网关)    │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌─────▼─────┐  ┌───────▼────────┐
   │  FastAPI    │  │  WebSocket │  │  Celery Worker │
   │  REST API   │  │  推送服务   │  │  异步任务队列   │
   │  (主服务)    │  │  (实时行情) │  │  (数据抓取/计算)│
   └──────┬──────┘  └─────┬─────┘  └───────┬────────┘
          │               │                │
          └───────────────┴────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
   ┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐
   │  PostgreSQL │ │    Redis    │ │  MinIO    │
   │  (关系数据)  │ │  (缓存/队列) │ │ (对象存储)│
   └─────────────┘ └─────────────┘ └───────────┘
```

---

## 2. 技术栈选型

| 层级 | 技术 | 说明 |
|------|------|------|
| Web 框架 | **FastAPI** | 异步支持、自动 OpenAPI 文档、Pydantic 校验 |
| 数据库 | **PostgreSQL 15+** | 关系数据存储，用户/股票元数据/新闻 |
| 时序扩展 | **TimescaleDB** | 基于 PostgreSQL 的时序数据库，存储股价历史 |
| 缓存/队列 | **Redis 7+** | 缓存热点数据、Session、Celery Broker |
| 任务队列 | **Celery + Celery Beat** | 定时抓取行情、数据清洗、指标计算 |
| 实时通信 | **WebSocket (原生)** | FastAPI 原生支持，推送实时行情 |
| 对象存储 | **MinIO** | 用户头像、报表导出、K线截图 |
| 部署 | **Docker + Docker Compose** | 开发/测试环境 |
| 生产部署 | **Kubernetes** | 容器编排、自动扩缩容 |
| 监控 | **Prometheus + Grafana** | 指标监控和告警 |
| 日志 | **Loki + Grafana** | 分布式日志收集 |

---

## 3. 模块划分

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理 (pydantic-settings)
│   │
│   ├── api/                    # API 路由层
│   │   ├── deps.py             # 依赖注入 (DB Session, 当前用户)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # 登录/注册/JWT
│   │   │   ├── user.py         # 用户管理
│   │   │   ├── stocks.py       # 股票基础信息
│   │   │   ├── quotes.py       # 实时行情 & 历史K线
│   │   │   ├── watchlist.py    # 自选股
│   │   │   ├── news.py         # 新闻资讯
│   │   │   ├── analysis.py     # 技术指标/分析
│   │   │   └── websocket.py    # WS 端点
│   │
│   ├── core/                   # 核心逻辑
│   │   ├── security.py         # 密码哈希 / JWT
│   │   ├── exceptions.py       # 自定义异常
│   │   └── middleware.py       # 中间件 (日志/限流/CORS)
│   │
│   ├── services/               # 业务服务层
│   │   ├── market_data.py      # 行情数据服务
│   │   ├── yahoo_finance.py    # Yahoo Finance 适配器
│   │   ├── alpha_vantage.py    # Alpha Vantage 适配器
│   │   ├── polygon.py          # Polygon.io 适配器
│   │   ├── technical_analysis.py # TA-Lib 指标计算
│   │   └── notification.py     # 推送通知服务
│   │
│   ├── models/                 # SQLAlchemy ORM 模型
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── stock.py
│   │   ├── quote.py
│   │   ├── watchlist.py
│   │   └── news.py
│   │
│   ├── schemas/                # Pydantic 数据模型
│   │   ├── user.py
│   │   ├── stock.py
│   │   ├── quote.py
│   │   └── analysis.py
│   │
│   ├── db/                     # 数据库
│   │   ├── session.py          # Session 工厂
│   │   ├── init_db.py          # 初始化/迁移
│   │   └── migrations/         # Alembic 迁移文件
│   │
│   ├── tasks/                  # Celery 异步任务
│   │   ├── sync_quotes.py      # 定时同步行情
│   │   ├── sync_intraday.py    # 分时数据同步
│   │   ├── calculate_indicators.py # 指标预计算
│   │   └── cleanup.py          # 数据清理
│   │
│   └── websocket/              # WebSocket 管理
│       ├── manager.py          # 连接管理器
│       └── handlers.py         # 消息处理器
│
├── tests/                      # 测试
├── alembic/                    # 数据库迁移
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml              # Poetry 依赖管理
└── requirements.txt
```

---

## 4. 数据库设计

### 4.1 ER 关系图

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    users     │       │  watchlists  │       │    stocks    │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │──┐    │ id (PK)      │       │ id (PK)      │
│ email        │  │    │ user_id (FK) │──────┼─│ symbol (UQ)  │
│ hashed_pw    │  └────│ stock_id (FK)│──────┘  │ name         │
│ full_name    │       │ created_at   │         │ sector       │
│ is_active    │       └──────────────┘         │ exchange     │
│ created_at   │                                │ is_active    │
└──────────────┘                                └──────────────┘
        │                                              │
        │         ┌──────────────────┐                 │
        │         │   daily_quotes   │                 │
        │         │  (TimescaleDB    │                 │
        │         │   hypertable)    │                 │
        │         ├──────────────────┤                 │
        │         │ time (PK)        │                 │
        └────────►│ stock_id (FK)    │◄────────────────┘
                  │ open             │
                  │ high             │
                  │ low              │
                  │ close            │
                  │ volume           │
                  │ adj_close        │
                  └──────────────────┘

┌──────────────┐       ┌──────────────┐
│   news       │       │  intraday    │
├──────────────┤       │  (Timescale  │
│ id (PK)      │       ├──────────────┤
│ stock_id(FK) │       │ time (PK)    │
│ title        │       │ stock_id(FK) │
│ source       │       │ price        │
│ url          │       │ volume       │
│ published_at │       └──────────────┘
│ sentiment    │
└──────────────┘
```

### 4.2 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    is_premium BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 股票基础信息表
CREATE TABLE stocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) UNIQUE NOT NULL,     -- "AAPL"
    name VARCHAR(200) NOT NULL,              -- "Apple Inc."
    sector VARCHAR(50),                      -- "Technology"
    industry VARCHAR(100),                   -- "Consumer Electronics"
    exchange VARCHAR(20),                    -- "NASDAQ"
    country VARCHAR(2) DEFAULT 'US',
    currency VARCHAR(3) DEFAULT 'USD',
    market_cap BIGINT,                       -- 市值
    shares_outstanding BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 自选股表
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID REFERENCES stocks(id) ON DELETE CASCADE,
    alert_high DECIMAL(12,4),                -- 价格上限提醒
    alert_low DECIMAL(12,4),                 -- 价格下限提醒
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, stock_id)
);

-- 日线行情 (TimescaleDB Hypertable)
CREATE TABLE daily_quotes (
    time TIMESTAMPTZ NOT NULL,
    stock_id UUID REFERENCES stocks(id),
    open DECIMAL(12,4) NOT NULL,
    high DECIMAL(12,4) NOT NULL,
    low DECIMAL(12,4) NOT NULL,
    close DECIMAL(12,4) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close DECIMAL(12,4),
    PRIMARY KEY (time, stock_id)
);

-- 转换为超表 (按时间自动分区)
SELECT create_hypertable('daily_quotes', 'time', chunk_time_interval => INTERVAL '7 days');

-- 创建索引加速查询
CREATE INDEX idx_daily_quotes_stock_time ON daily_quotes(stock_id, time DESC);

-- 分时数据 (TimescaleDB Hypertable, 保留7天)
CREATE TABLE intraday_quotes (
    time TIMESTAMPTZ NOT NULL,
    stock_id UUID REFERENCES stocks(id),
    price DECIMAL(12,4) NOT NULL,
    volume BIGINT,
    PRIMARY KEY (time, stock_id)
);
SELECT create_hypertable('intraday_quotes', 'time', chunk_time_interval => INTERVAL '1 day');

-- 新闻表
CREATE TABLE news (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id UUID REFERENCES stocks(id),
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    source VARCHAR(100),
    url VARCHAR(1000),
    image_url VARCHAR(1000),
    sentiment DECIMAL(3,2),   -- -1.0 到 1.0
    published_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_news_stock_published ON news(stock_id, published_at DESC);
```

---

## 5. API 设计

### 5.1 REST API

```yaml
# 认证
POST   /api/v1/auth/register           # 注册
POST   /api/v1/auth/login              # 登录 (返回 JWT)
POST   /api/v1/auth/refresh            # 刷新 Token
POST   /api/v1/auth/logout             # 登出

# 用户
GET    /api/v1/users/me                # 获取当前用户信息
PUT    /api/v1/users/me                # 更新用户信息
POST   /api/v1/users/me/avatar         # 上传头像

# 股票基础
GET    /api/v1/stocks                  # 股票列表 (分页/搜索)
GET    /api/v1/stocks/{symbol}         # 股票详情
GET    /api/v1/stocks/search?q=AAPL   # 搜索股票

# 行情数据
GET    /api/v1/quotes/{symbol}         # 最新报价
GET    /api/v1/quotes/{symbol}/history # 历史K线
  Query: ?interval=1d|1wk|1mo&range=1mo|3mo|1y|5y|max
GET    /api/v1/quotes/{symbol}/intraday # 当日分时

# 自选股
GET    /api/v1/watchlist               # 获取自选股列表
POST   /api/v1/watchlist               # 添加自选股
DELETE /api/v1/watchlist/{symbol}      # 删除自选股
PUT    /api/v1/watchlist/{symbol}      # 更新提醒价格

# 技术分析
GET    /api/v1/analysis/{symbol}/indicators  # 技术指标
  Query: ?indicators=rsi,macd,bollinger,sma50,sma200
GET    /api/v1/analysis/{symbol}/chart       # 图表数据 (含指标)
POST   /api/v1/analysis/screen               # 股票筛选器

# 新闻
GET    /api/v1/news                      # 综合新闻
GET    /api/v1/news/{symbol}             # 个股新闻
GET    /api/v1/news/{symbol}/sentiment   # 情感分析

# 市场概览
GET    /api/v1/market/indices            # 主要指数
GET    /api/v1/market/movers             # 涨跌榜
GET    /api/v1/market/sector-performance # 板块表现
```

### 5.2 WebSocket 协议

```javascript
// 连接
ws://api.protrade.com/ws/v1/quotes

// 认证 (连接后第一条消息)
{
  "type": "auth",
  "token": "Bearer eyJhbG..."
}

// 订阅行情
{
  "type": "subscribe",
  "symbols": ["AAPL", "MSFT", "NVDA", "TSLA"]
}

// 取消订阅
{
  "type": "unsubscribe",
  "symbols": ["TSLA"]
}

// 服务端推送 (实时报价)
{
  "type": "quote",
  "data": {
    "symbol": "AAPL",
    "price": 232.45,
    "change": 2.87,
    "change_percent": 1.25,
    "volume": 45230000,
    "timestamp": "2025-01-15T14:32:01Z"
  }
}

// 服务端推送 (批量快照)
{
  "type": "snapshot",
  "data": [
    {"symbol": "AAPL", "price": 232.45, ...},
    {"symbol": "MSFT", "price": 441.78, ...}
  ]
}
```

---

## 6. 数据流设计

### 6.1 行情数据同步流程

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Yahoo Finance  │     │  Alpha Vantage  │     │   Polygon.io    │
│   (免费/备用)    │     │   (免费/备用)    │     │  (专业/实时)    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Data Adapter         │
                    │  (统一数据格式/异常处理)   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      Celery Worker        │
                    │  - sync_daily_quotes      │
                    │  - sync_intraday          │
                    │  - sync_stock_info        │
                    └─────────────┬─────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐ ┌────────▼────────┐ ┌───────▼─────────┐
     │   PostgreSQL    │ │    TimescaleDB  │ │      Redis      │
     │  (股票元数据)    │ │   (价格历史)     │ │  (实时缓存)      │
     └─────────────────┘ └─────────────────┘ └─────────────────┘
              │                   │                   │
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      FastAPI / WS         │
                    │      (响应客户端)          │
                    └───────────────────────────┘
```

### 6.2 实时推送流程

```
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│  交易所/API   │─────▶│  消息解析器   │─────▶│  Redis Pub/Sub   │
│  (Polygon)   │      │              │      │  (quote_channel) │
└──────────────┘      └──────────────┘      └────────┬─────────┘
                                                     │
                              ┌──────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  WebSocket Manager │
                    │  (连接/订阅管理)    │
                    └─────────┬──────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
  ┌──────▼─────┐       ┌─────▼─────┐       ┌─────▼─────┐
  │  用户 A    │       │  用户 B   │       │  用户 C   │
  │ (订阅AAPL) │       │(订阅MSFT) │       │(订阅全部) │
  └────────────┘       └───────────┘       └───────────┘
```

---

## 7. 核心服务实现要点

### 7.1 行情数据服务 (market_data.py)

```python
class MarketDataService:
    """行情数据服务 — 缓存优先策略"""

    async def get_quote(self, symbol: str) -> Quote:
        # 1. 查 Redis 实时缓存 (TTL 60s)
        cache_key = f"quote:{symbol}"
        if cached := await redis.get(cache_key):
            return Quote.parse_raw(cached)

        # 2. 查数据库最新记录
        quote = await self.db.get_latest_quote(symbol)
        if quote and quote.is_fresh():
            return quote

        # 3. 回源拉取 (限流保护)
        quote = await self.fetch_from_provider(symbol)
        await redis.setex(cache_key, 60, quote.json())
        return quote

    async def get_history(
        self,
        symbol: str,
        interval: str = "1d",
        range_: str = "1y"
    ) -> list[OHLCV]:
        # TimescaleDB 连续聚合查询 (已预计算常见周期)
        return await self.db.query_ohlcv(symbol, interval, range_)
```

### 7.2 WebSocket 连接管理器

```python
class ConnectionManager:
    """管理 WebSocket 连接和订阅映射"""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}          # user_id -> ws
        self.subscriptions: dict[str, set[str]] = {}          # symbol -> {user_ids}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[user_id] = ws

    def subscribe(self, user_id: str, symbols: list[str]):
        for sym in symbols:
            self.subscriptions.setdefault(sym, set()).add(user_id)

    async def broadcast(self, symbol: str, data: dict):
        """向订阅了某股票的所有用户推送"""
        if symbol not in self.subscriptions:
            return
        message = json.dumps({"type": "quote", "data": data})
        for user_id in self.subscriptions[symbol]:
            if ws := self.connections.get(user_id):
                await ws.send_text(message)
```

### 7.3 技术指标计算

```python
class TechnicalAnalysis:
    """基于 pandas-ta / TA-Lib 的技术指标"""

    def calculate(self, df: pd.DataFrame, indicators: list[str]) -> dict:
        result = {}

        if "rsi" in indicators:
            result["rsi"] = ta.rsi(df["close"], length=14)

        if "macd" in indicators:
            macd = ta.macd(df["close"])
            result["macd"] = {
                "macd": macd["MACD_12_26_9"],
                "signal": macd["MACDs_12_26_9"],
                "histogram": macd["MACDh_12_26_9"]
            }

        if "bollinger" in indicators:
            bb = ta.bbands(df["close"], length=20, std=2)
            result["bollinger"] = {
                "upper": bb["BBU_20_2.0"],
                "middle": bb["BBM_20_2.0"],
                "lower": bb["BBL_20_2.0"]
            }

        if "sma50" in indicators:
            result["sma50"] = ta.sma(df["close"], length=50)

        if "sma200" in indicators:
            result["sma200"] = ta.sma(df["close"], length=200)

        return result
```

---

## 8. Celery 定时任务

```python
# tasks/schedule.py

celery_app.conf.beat_schedule = {
    # 实时行情 (交易日 9:30-16:00 ET, 每 30 秒)
    "sync-realtime-quotes": {
        "task": "app.tasks.sync_quotes.sync_intraday",
        "schedule": 30.0,
        "args": ("us_equity",),
    },

    # 收盘后同步日线 (每天 18:00 ET)
    "sync-daily-quotes": {
        "task": "app.tasks.sync_quotes.sync_daily",
        "schedule": crontab(hour=18, minute=0),
    },

    # 同步股票基础信息 (每周一次)
    "sync-stock-info": {
        "task": "app.tasks.sync_quotes.sync_stock_info",
        "schedule": crontab(day_of_week="sun", hour=2, minute=0),
    },

    # 预计算技术指标 (每天收盘后)
    "calculate-indicators": {
        "task": "app.tasks.calculate_indicators.run_all",
        "schedule": crontab(hour=19, minute=0),
    },

    # 清理过期分时数据 (保留 7 天)
    "cleanup-intraday": {
        "task": "app.tasks.cleanup.drop_old_intraday",
        "schedule": crontab(hour=3, minute=0),
    },

    # 新闻抓取 (每小时)
    "sync-news": {
        "task": "app.tasks.sync_news.fetch_all",
        "schedule": 3600.0,
    },
}
```

---

## 9. 缓存策略

| 数据类型 | 缓存层 | TTL | 策略 |
|----------|--------|-----|------|
| 实时报价 | Redis | 60s | 写穿透，懒加载 |
| 股票列表 | Redis | 1h | 全量缓存，定时刷新 |
| 历史K线 | Redis | 1d | 按 symbol+interval 缓存 |
| 技术指标 | Redis | 1d | 收盘后预计算缓存 |
| 用户Session | Redis | 7d | JWT Blacklist |
| 新闻列表 | Redis | 10min | 懒加载 |
| 市场概览 | Redis | 30s | 定时更新 |

---

## 10. 安全设计

```
┌──────────────────────────────────────────┐
│              安全层                       │
├──────────────────────────────────────────┤
│  HTTPS / TLS 1.3                         │
│  CORS 白名单限制                          │
│  Rate Limiting (Redis + slowapi)         │
│    - 匿名: 30 req/min                    │
│    - 登录: 120 req/min                   │
│    - 实时WS: 1 连接/用户                 │
├──────────────────────────────────────────┤
│  JWT 认证 (access_token + refresh_token) │
│  - Access: 15min                         │
│  - Refresh: 7 days                       │
│  - 黑名单存储于 Redis                     │
├──────────────────────────────────────────┤
│  输入校验 (Pydantic / SQL注入防护)        │
│  参数化查询 (SQLAlchemy)                 │
├──────────────────────────────────────────┤
│  API Key 管理 (外部数据提供商)            │
│  - 轮换机制                               │
│  - 熔断降级                               │
└──────────────────────────────────────────┘
```

---

## 11. 部署架构 (生产)

```
┌──────────────────────────────────────────────────────────────┐
│                         用户请求                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │      CloudFlare          │
              │   (DDoS / CDN / WAF)     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │      Nginx Ingress       │
              │   (SSL / 负载均衡)        │
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ FastAPI │       │ FastAPI │       │ FastAPI │   (HPA: 3-10 pods)
   │ Pod 1   │       │ Pod 2   │       │ Pod 3   │
   └────┬────┘       └────┬────┘       └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │PostgreSQL│      │  Redis  │       │  Celery │
   │Primary  │◄────►│ Cluster │◄────►│ Workers │
   │Replica  │       │         │       │ Beat    │
   └─────────┘       └─────────┘       └─────────┘
```

---

## 12. 开发环境启动

```yaml
# docker-compose.yml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/protrade
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: protrade
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery-worker:
    build: .
    command: celery -A app.tasks worker -l info
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A app.tasks beat -l info
    depends_on:
      - db
      - redis

volumes:
  pgdata:
```

---

## 13. 前端对接要点

| 前端功能 | 后端接口 | 说明 |
|----------|----------|------|
| 指数卡片 | `GET /market/indices` | 30s 轮询 |
| 个股切换 | `GET /quotes/{symbol}` | 缓存 60s |
| K线图 | `GET /quotes/{symbol}/history` | 按时间范围请求 |
| 实时价格 | WebSocket `subscribe` | 推送更新 |
| 自选股 | CRUD `/watchlist` | 需登录 |
| 技术指标 | `GET /analysis/{symbol}/indicators` | 批量计算 |

---

## 14. 扩展路线

| 阶段 | 功能 | 技术 |
|------|------|------|
| v1.0 | 基础行情 + 自选股 | FastAPI + TimescaleDB |
| v1.5 | 实时推送 + 新闻 | WebSocket + NLP 情感分析 |
| v2.0 | 高级图表 + 回测 | 自定义指标 DSL + Backtrader |
| v2.5 | 模拟交易 + 组合 | 虚拟资产系统 + 收益分析 |
| v3.0 | AI 预测 + 预警 | 时序模型 (Prophet/LSTM) |

---

## 15. 费用估算 (数据提供商)

| 提供商 | 免费额度 | 付费起步 | 特点 |
|--------|----------|----------|------|
| **Yahoo Finance** | 无限制 | 免费 | 非官方 API，可能不稳定 |
| **Alpha Vantage** | 25 次/天 | $49.99/月 | 基本面数据丰富 |
| **Polygon.io** | 无 | $49/月 | 官方实时数据，质量高 |
| **Finnhub** | 60 次/分 | 免费够用 | 实时 WebSocket 免费 |
| **IEX Cloud** | 有限 | $19/月 | 美国市场深度数据 |

> 推荐起步组合：**Finnhub (实时) + Yahoo Finance (历史)**，成本最低。业务稳定后迁移到 **Polygon.io**。
