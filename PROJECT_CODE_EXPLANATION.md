# Hoop Insight 项目代码讲解文档

> 说明：本文档基于当前工作区代码阅读整理，只解释现有实现，不修改任何功能代码。  
> 当前项目不是 Streamlit，也不是 Next.js，而是 **FastAPI 后端 + React/Vite 前端** 的前后端分离篮球数据分析平台。

---

## 一、项目整体概览

### 1. 这个项目整体是做什么的

Hoop Insight 是一个篮球数据分析 / 智能问数平台。它把 NBA 相关数据从数据源获取出来，经过缓存、整理、指标计算，再通过前端页面展示成数据总览、近期比赛、球员分析、球队分析、投篮分析和智能问数等模块。

从用户视角看，它解决的是：

- 快速查看近期比赛和今日比赛；
- 进入单场比赛复盘，查看比分走势、关键节点、球队对比和高影响力球员；
- 查看球员基础数据榜单、高级数据和能力雷达图；
- 查看球队进攻、防守、净效率、节奏等表现；
- 查看球员或球队的投篮分布、热区和高效区域；
- 用自然语言向系统提问，由后端组织数据上下文，再让大模型生成分析回答。

它不是单纯的表格展示，而是把 **数据获取、数据分析、图表表达和 AI 总结** 串成了一条完整的数据应用链路。

### 2. 使用了哪些技术栈

后端：

- Python
- FastAPI
- Pydantic / pydantic-settings
- pandas
- nba_api
- requests
- SQLAlchemy
- pytest
- 本地 JSON 文件缓存

前端：

- React
- TypeScript
- Vite
- react-router-dom
- fetch API
- 手写 SVG / CSS 图表

数据与配置：

- `backend/.env.example`：后端环境变量示例
- `data/cache/nba/`：NBA API 响应缓存 JSON
- `data/processed/`：demo 模式预期读取的处理后数据目录，目前当前扫描为空
- `scripts/export_demo_data.py`：把缓存导出成 demo CSV/JSON 的脚本

AI：

- 兼容 OpenAI Chat Completions 格式的大模型接口
- 通过 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 配置

### 3. 项目运行入口在哪里

后端入口：

- 文件：`backend/app/main.py`
- 启动命令：

```bash
cd backend
uvicorn app.main:app --reload
```

前端入口：

- HTML 入口：`frontend/index.html`
- React 入口：`frontend/src/main.tsx`
- 应用壳入口：`frontend/src/App.tsx`
- 启动命令：

```bash
cd frontend
npm run dev
```

默认访问：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`

### 4. 页面/模块之间的大致关系

前端路由由 `frontend/src/main.tsx` 定义：

```text
/              数据总览 Dashboard
/games         近期比赛 Games
/games/:gameId 单场比赛复盘 GameDetail
/players       球员分析 Players
/teams         球队分析 Teams
/shots         投篮分析 Shots
/ask-ai        智能问数 AskAI
```

所有页面都包在 `App.tsx` 和 `Layout.tsx` 里：

```text
main.tsx 路由
  -> App.tsx 根据 URL 选择页面标题和描述
    -> Layout.tsx 渲染侧边栏、顶部栏、主内容区
      -> 具体页面组件
```

后端接口按模块划分：

```text
/api/games   比赛相关
/api/players 球员相关
/api/teams   球队相关
/api/shots   投篮相关
/api/ai      智能问数和报告生成
```

### 5. 项目属于哪一类

它同时具备三类特征，但主类型是 **数据分析型 + AI 应用型**。

- 前端展示型：有完整 React 页面、导航、卡片、表格、图表。
- 数据分析型：核心逻辑在 pandas 数据处理、指标聚合、榜单排序、雷达图归一化、投篮区域效率分析。
- AI 应用型：智能问数模块会调用兼容 OpenAI 的大模型接口，把结构化数据作为上下文传给模型生成回答。

如果答辩时要一句话定位，可以说：

> Hoop Insight 是一个以篮球结构化数据分析为核心、前端可视化为表现形式、LLM 智能问数为扩展能力的前后端分离数据分析平台。

---

## 二、项目目录结构讲解

### 1. 主要目录树

已排除 `.venv`、`node_modules`、`dist`、缓存和 `__pycache__` 后，主要结构如下：

```text
hoop-insight/
├─ README.md
├─ PROJECT_CODE_EXPLANATION.md
├─ backend/
│  ├─ .env
│  ├─ .env.example
│  ├─ requirements.txt
│  ├─ pytest.ini
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  ├─ ai.py
│  │  │  ├─ games.py
│  │  │  ├─ players.py
│  │  │  ├─ shots.py
│  │  │  └─ teams.py
│  │  ├─ analytics/
│  │  │  ├─ game_flow.py
│  │  │  ├─ metrics.py
│  │  │  ├─ normalization.py
│  │  │  └─ shot_analysis.py
│  │  ├─ core/
│  │  │  ├─ cache.py
│  │  │  └─ config.py
│  │  ├─ db/
│  │  │  └─ database.py
│  │  ├─ schemas/
│  │  │  ├─ ai.py
│  │  │  ├─ game.py
│  │  │  ├─ player.py
│  │  │  ├─ shot.py
│  │  │  └─ team.py
│  │  └─ services/
│  │     ├─ ai_service.py
│  │     ├─ game_service.py
│  │     ├─ nba_client.py
│  │     ├─ player_service.py
│  │     ├─ query_service.py
│  │     ├─ shot_service.py
│  │     └─ team_service.py
│  ├─ docs/
│  │  └─ games_api_examples.md
│  └─ tests/
│     ├─ test_ai_unconfigured.py
│     ├─ test_cache.py
│     ├─ test_game_flow.py
│     ├─ test_game_review.py
│     ├─ test_game_service.py
│     ├─ test_nba_client_demo.py
│     ├─ test_normalization.py
│     ├─ test_player_service.py
│     ├─ test_query_service.py
│     ├─ test_shot_analysis.py
│     ├─ test_shot_service.py
│     └─ test_team_service.py
├─ data/
│  ├─ cache/
│  │  └─ nba/
│  │     └─ *.json
│  ├─ processed/
│  └─ raw/
├─ docs/
│  └─ demo_script.md
├─ frontend/
│  ├─ index.html
│  ├─ package.json
│  ├─ tsconfig.json
│  ├─ vite.config.ts
│  └─ src/
│     ├─ main.tsx
│     ├─ App.tsx
│     ├─ analytics/
│     │  └─ metricExplanations.ts
│     ├─ api/
│     │  ├─ client.ts
│     │  └─ formatters.ts
│     ├─ charts/
│     │  ├─ GameFlowChart.tsx
│     │  ├─ HeatMap.tsx
│     │  ├─ RadarChart.tsx
│     │  └─ ShotChart.tsx
│     ├─ components/
│     │  ├─ AsyncState.tsx
│     │  ├─ ChartCard.tsx
│     │  ├─ DataTable.tsx
│     │  ├─ Layout.tsx
│     │  ├─ Sidebar.tsx
│     │  └─ StatCard.tsx
│     ├─ constants/
│     │  └─ zhLabels.ts
│     ├─ pages/
│     │  ├─ AskAI.tsx
│     │  ├─ Dashboard.tsx
│     │  ├─ GameDetail.tsx
│     │  ├─ Games.tsx
│     │  ├─ Players.tsx
│     │  ├─ Shots.tsx
│     │  └─ Teams.tsx
│     └─ styles/
│        └─ globals.css
├─ notebooks/
└─ scripts/
   └─ export_demo_data.py
```

### 2. 后端目录说明

#### `backend/app/main.py`

作用：

- 创建 FastAPI 应用；
- 配置 CORS；
- 注册 AI、比赛、球员、投篮、球队路由；
- 提供 `/health` 健康检查接口。

核心性：

- 后端启动入口，是 `uvicorn app.main:app --reload` 中的 `app` 来源。

#### `backend/app/api/`

作用：

- 定义 HTTP API 层；
- 接收 query/path/body 参数；
- 调用 services 层；
- 使用 schemas 层定义 response_model。

文件：

- `games.py`：近期比赛、今日比赛、焦点比赛、单场复盘。
- `players.py`：球员榜单、高级数据、球员画像、雷达图。
- `teams.py`：球队总览、进攻、防守、单队画像。
- `shots.py`：球员/球队 Shot Chart 和投篮区域分析。
- `ai.py`：智能问数、比赛报告、球员报告、球队报告。

核心文件：

- 全部都是核心接口文件，但真正业务计算不在这里，而在 `services/` 和 `analytics/`。

#### `backend/app/services/`

作用：

- 业务服务层；
- 把 NBA API 或 demo/cache 数据转换成前端需要的结构；
- 调用 `analytics/` 做指标计算。

文件：

- `nba_client.py`：统一获取 NBA 数据、读取 demo 数据、写入/读取缓存。
- `game_service.py`：比赛列表、今日比赛、焦点比赛、单场复盘。
- `player_service.py`：球员榜单、高级数据、画像、雷达图。
- `team_service.py`：球队总览、进攻、防守、画像、图表点。
- `shot_service.py`：投篮图、区域汇总、高效区域识别。
- `ai_service.py`：调用大模型接口，构造 prompt。
- `query_service.py`：智能问数的意图识别、实体抽取、结构化数据查询。

核心文件：

- `nba_client.py` 是数据入口核心；
- `query_service.py` 是 AI 问数核心；
- `player_service.py`、`team_service.py`、`shot_service.py`、`game_service.py` 是四大业务模块核心。

#### `backend/app/analytics/`

作用：

- 放和数据分析算法直接相关的函数；
- 尽量不处理 HTTP；
- 多数输入输出是 pandas DataFrame 或普通 dict/list。

文件：

- `game_flow.py`：从逐回合数据构建比分走势、关键节点和比赛摘要。
- `normalization.py`：球员雷达图 0-100 分归一化。
- `shot_analysis.py`：投篮区域聚合、高效区域识别。
- `metrics.py`：篮球指标解释、球队进攻/防守指标说明。

核心文件：

- `game_flow.py`
- `normalization.py`
- `shot_analysis.py`

#### `backend/app/schemas/`

作用：

- 定义 Pydantic 模型；
- 约束 API 返回字段；
- 让前端拿到稳定 JSON 结构。

文件：

- `game.py`：比赛响应模型。
- `player.py`：球员榜单、高级数据、雷达图模型。
- `team.py`：球队 KPI、表格、图表、画像模型。
- `shot.py`：投篮点、区域、总计模型。
- `ai.py`：AI 请求和响应模型。

初学者重点：

- Pydantic 模型类似“接口契约”，它说明后端返回给前端的数据长什么样。

#### `backend/app/core/`

作用：

- 项目通用基础设施。

文件：

- `config.py`：环境变量读取。
- `cache.py`：本地 JSON 缓存。

#### `backend/app/db/database.py`

作用：

- 配置 SQLAlchemy engine、SessionLocal、Base。

当前现状：

- 当前业务主线没有明显使用数据库表模型；
- README 里提到 SQLite，但代码实际主要使用 `data/cache/nba/*.json` 做 NBA API 缓存；
- 这个文件更像为未来数据库持久化预留。

#### `backend/tests/`

作用：

- 覆盖缓存、demo 数据读取、比赛走势、球员、球队、投篮、AI 未配置等逻辑。

核心意义：

- 对答辩很有价值，可以说明项目不是只写页面，还对关键数据逻辑做了测试。

### 3. 前端目录说明

#### `frontend/src/main.tsx`

作用：

- React 应用入口；
- 创建 Browser Router；
- 定义所有页面路由；
- 把 `<RouterProvider />` 挂载到 DOM 的 `root`。

#### `frontend/src/App.tsx`

作用：

- 根据当前 URL 选择页面标题和描述；
- 渲染统一布局；
- 使用 `<Outlet />` 显示子路由页面。

#### `frontend/src/api/client.ts`

作用：

- 前端请求后端 API 的统一入口；
- 定义 TypeScript 类型；
- 封装 `request()`、`useApi()`；
- 提供 `getRecentGames()`、`getPlayerLeaderboard()`、`askAI()` 等函数。

核心性：

- 前端数据流中心。所有页面几乎都从这里拿数据。

#### `frontend/src/api/formatters.ts`

作用：

- 把后端原始字段格式化成页面可显示文本；
- 例如数字格式、百分比格式、比赛对阵文本、表格行。

#### `frontend/src/components/`

作用：

- 可复用 UI 组件。

文件：

- `Layout.tsx`：整体布局。
- `Sidebar.tsx`：侧边导航。
- `StatCard.tsx`：KPI 卡片。
- `DataTable.tsx`：通用表格。
- `ChartCard.tsx`：简化柱状图/折线图卡片。
- `AsyncState.tsx`：loading/error/empty 状态。

#### `frontend/src/charts/`

作用：

- 图表组件。

文件：

- `GameFlowChart.tsx`：比赛比分走势折线图。
- `RadarChart.tsx`：球员能力雷达图。
- `ShotChart.tsx`：投篮散点图。
- `HeatMap.tsx`：投篮热区图。

特点：

- 这些图没有用 ECharts/Recharts，而是用 React + SVG 手写。

#### `frontend/src/pages/`

作用：

- 具体业务页面。

文件：

- `Dashboard.tsx`：数据总览。
- `Games.tsx`：近期比赛。
- `GameDetail.tsx`：单场复盘。
- `Players.tsx`：球员分析。
- `Teams.tsx`：球队分析。
- `Shots.tsx`：投篮分析。
- `AskAI.tsx`：智能问数。

#### `frontend/src/constants/zhLabels.ts`

作用：

- 页面中文文案、导航、指标标签、投篮区域标签、雷达图标签。

注意：

- 当前终端读取时大量中文显示为乱码。答辩时如果页面本身也乱码，需要优先修复文件编码或保存格式；如果页面正常，可能只是终端编码显示问题。

### 4. 数据目录说明

#### `data/cache/nba/`

作用：

- 存放 NBA API 调用结果缓存。
- 文件名是哈希值，如 `118ae...json`。

缓存结构大致是：

```json
{
  "created_at": 123,
  "expires_at": 456,
  "data": {}
}
```

#### `data/processed/`

作用：

- demo 模式下预期存放 CSV/JSON，例如：
  - `games.csv`
  - `scoreboard.json`
  - `players_base.csv`
  - `players_advanced.csv`
  - `teams_base.csv`
  - `teams_advanced.csv`
  - `shots.csv`
  - `play_by_play.csv`
  - `box_scores.csv`

当前扫描结果：

- 目录存在，但当前为空。

#### `data/raw/`

作用：

- 预留原始数据目录。

当前扫描结果：

- 目录存在，但当前为空。

---

## 三、项目启动流程讲解

### 1. 后端启动流程

启动命令：

```bash
cd backend
uvicorn app.main:app --reload
```

执行顺序：

```text
uvicorn 找到 app.main:app
  -> 执行 backend/app/main.py
    -> get_settings() 读取配置
    -> 创建 FastAPI(title=settings.app_name)
    -> 添加 CORS 中间件
    -> include_router 注册各模块路由
    -> 暴露 /health
```

关键代码分块：

```python
settings = get_settings()
app = FastAPI(title=settings.app_name)
```

解释：

- `get_settings()` 从环境变量或 `.env` 读取配置；
- `settings.app_name` 决定 FastAPI 文档里的应用标题；
- `app` 是后端应用实例。

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

解释：

- 前端开发服务器默认在 5173；
- 浏览器跨域请求后端 8000 时需要 CORS 允许；
- 这里允许本地前端访问所有方法和请求头。

```python
app.include_router(ai_router)
app.include_router(games_router)
app.include_router(players_router)
app.include_router(shots_router)
app.include_router(teams_router)
```

解释：

- 把各模块 API 注册进主应用；
- 注册后 `/api/games/recent`、`/api/players/leaderboard` 等接口才可访问。

### 2. 前端启动流程

启动命令：

```bash
cd frontend
npm run dev
```

`package.json` 中：

```json
"scripts": {
  "dev": "vite",
  "typecheck": "tsc -b",
  "build": "tsc -b && vite build",
  "preview": "vite preview"
}
```

执行顺序：

```text
npm run dev
  -> vite 启动开发服务器
  -> 浏览器加载 index.html
  -> index.html 加载 src/main.tsx
  -> main.tsx 创建 React Router
  -> App.tsx 渲染 Layout
  -> 当前路由对应页面懒加载
  -> 页面调用 client.ts 中的 API 函数
  -> 后端返回 JSON
  -> 页面渲染 KPI、表格、图表
```

### 3. React 路由、组件和页面入口

`frontend/src/main.tsx` 中的核心结构：

```tsx
const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, lazy: () => import("./pages/Dashboard") },
      { path: "games", lazy: () => import("./pages/Games") },
      { path: "games/:gameId", lazy: () => import("./pages/GameDetail") },
      ...
    ],
  },
]);
```

分块解释：

- `path: "/"`：根路径；
- `element: <App />`：所有子页面共享 `App`；
- `children`：子路由；
- `index: true`：访问 `/` 时加载 Dashboard；
- `lazy`：懒加载页面，只有访问对应路由时才下载对应模块；
- `games/:gameId`：动态路由，`GameDetail.tsx` 通过 `useParams()` 获取 `gameId`。

### 4. 环境变量、API Key、配置文件在哪里读取

后端配置：

- 文件：`backend/app/core/config.py`
- 示例：`backend/.env.example`

配置项：

```env
APP_NAME=hoop-insight
ENV=development
DATABASE_URL=sqlite:///../data/cache/hoop_insight.db
NBA_CACHE_DIR=../data/cache/nba
DEMO_MODE=false
DEMO_DATA_DIR=../data/processed
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

关键代码：

```python
class Settings(BaseSettings):
    app_name: str = Field(default="hoop-insight", alias="APP_NAME")
    nba_cache_dir: str = Field(default="../data/cache/nba", alias="NBA_CACHE_DIR")
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

解释：

- `BaseSettings` 会自动从环境变量读取；
- `env_file=".env"` 表示也会读 `backend/.env`；
- `alias` 是真正的环境变量名；
- `extra="ignore"` 表示 `.env` 里多余字段忽略。

前端配置：

- 文件：`frontend/src/api/client.ts`

```ts
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
```

解释：

- 如果前端环境变量里有 `VITE_API_BASE_URL`，就用它；
- 否则默认请求本地后端 `http://127.0.0.1:8000`。

---

## 四、数据流讲解

### 总数据流

```text
原始数据
  -> nba_api 或 data/processed demo 文件
  -> nba_client.py 读取
  -> cache.py 缓存
  -> service 层清洗、筛选、聚合
  -> analytics 层计算指标
  -> schemas 层转为响应模型
  -> FastAPI 返回 JSON
  -> frontend/src/api/client.ts 请求
  -> 页面组件接收数据
  -> KPI 卡片 / 表格 / SVG 图表展示
```

### 1. 原始数据来源在哪里

主要有三种来源：

1. NBA API 实时/历史数据：
   - `nba_api.live.nba.endpoints.scoreboard.ScoreBoard`
   - `nba_api.stats.endpoints.leaguegamelog.LeagueGameLog`
   - `nba_api.stats.endpoints.leaguedashplayerstats.LeagueDashPlayerStats`
   - `nba_api.stats.endpoints.leaguedashteamstats.LeagueDashTeamStats`
   - `nba_api.stats.endpoints.shotchartdetail.ShotChartDetail`
   - `nba_api.stats.endpoints.playbyplayv2.PlayByPlayV2`
   - `nba_api.stats.endpoints.boxscoretraditionalv2.BoxScoreTraditionalV2`

2. 本地缓存：
   - `data/cache/nba/*.json`

3. demo 数据：
   - 由 `DEMO_MODE=true` 开启；
   - 从 `DEMO_DATA_DIR` 读取；
   - 默认目录为 `../data/processed`。

### 2. 数据文件或 API 如何读取

核心文件：`backend/app/services/nba_client.py`

以球员数据为例：

```python
def get_player_stats(season: str, measure_type: str = "Base"):
    params = {"season": season, "measure_type": measure_type}

    def fetcher() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashplayerstats
        endpoint = leaguedashplayerstats.LeagueDashPlayerStats(...)
        return endpoint.get_data_frames()[0]

    return _get_cached_dataframe(
        "leaguedashplayerstats",
        params,
        SEASON_CACHE_TTL_SECONDS,
        fetcher,
    )
```

分块解释：

- `season`：赛季，例如 `2025-26`；
- `measure_type`：统计类型，例如 `Base` 或 `Advanced`；
- `params`：用于生成缓存 key；
- `fetcher()`：真正调用 NBA API；
- `_get_cached_dataframe()`：先查 demo，再查缓存，最后才调用 API。

### 3. 数据清洗在哪里完成

清洗分散在 service 层和 analytics 层。

常见清洗函数：

- `_safe_int()`
- `_safe_float()`
- `_safe_date()`
- `_safe_str()`

作用：

- 防止 `None`、`NaN`、字符串数字导致接口报错；
- 把 pandas / NBA API 数据转成 JSON 友好的 Python 基础类型。

投篮清洗：

- 文件：`backend/app/services/shot_service.py`
- 函数：`_prepare_shot_dataframe()`

它会：

- 补齐缺失列；
- 转换 `LOC_X`、`LOC_Y`；
- 转换 `SHOT_MADE_FLAG`；
- 根据 `SHOT_TYPE` 判断 2 分/3 分；
- 计算每次出手得到的 `POINTS`。

比赛走势清洗：

- 文件：`backend/app/analytics/game_flow.py`
- 函数：`build_game_flow()`

它会：

- 找到 period、clock、score、margin 等列；
- 解析比分；
- 按回合构造主客队累计得分；
- 计算分差。

### 4. 指标在哪里计算

项目中指标分两类。

第一类：NBA API 已经给出的字段。

例如：

- `PTS`
- `REB`
- `AST`
- `FG_PCT`
- `OFF_RATING`
- `DEF_RATING`
- `NET_RATING`
- `TS_PCT`
- `EFG_PCT`
- `USG_PCT`
- `PACE`

项目主要负责读取、筛选、排序和展示。

第二类：项目自己计算的字段。

例如：

- 投篮区域 `FGA`、`FGM`、`FG_PCT`、`POINTS`、`PPS`
- 球员雷达图 0-100 分
- 比赛最大领先、领先变化、平分次数
- 单场球员 `IMPACT_SCORE`
- 焦点比赛 `focus_score`

### 5. DataFrame / JSON / API 返回值如何传递

后端内部：

```text
nba_client 返回 pd.DataFrame 或 dict
  -> service 层处理 DataFrame
  -> 创建 Pydantic Response 模型
  -> FastAPI 自动转 JSON
```

前端内部：

```text
client.ts 的 request<T>() fetch JSON
  -> useApi() 管理 loading/error/data
  -> 页面组件读取 data
  -> formatter 转显示格式
  -> 组件渲染
```

### 6. 标准格式举例

#### 数据总览

```text
NBA 球队统计
  -> nba_client.get_team_stats()
  -> team_service.get_team_overview()
  -> TeamModuleResponse
  -> getTeamOverview()
  -> Dashboard.tsx
  -> StatCard / ChartCard / DataTable
```

#### 投篮分析

```text
ShotChartDetail 原始出手坐标
  -> get_shot_chart_detail()
  -> shot_service._prepare_shot_dataframe()
  -> shot_analysis.get_shot_zone_summary()
  -> ShotChartResponse / ShotZoneResponse
  -> Shots.tsx
  -> ShotChart / HeatMap / EfficiencyList
```

#### 智能问数

```text
用户问题
  -> AskAI.tsx 调 askAI()
  -> POST /api/ai/ask
  -> query_service.classify_question()
  -> query_service.query_structured_data()
  -> ai_service.answer_question()
  -> AskAI.tsx 展示 MarkdownCard
```

---

## 五、页面模块逐个讲解

### 1. 数据总览页面

文件：

- `frontend/src/pages/Dashboard.tsx`

页面作用：

- 作为首页；
- 快速展示球队总览 KPI、球队效率图和近期比赛表；
- 帮用户进入其他分析模块前先建立整体印象。

使用数据：

- `getRecentGames()`：近期比赛。
- `getTeamOverview()`：球队总览。

后端对应：

- `GET /api/games/recent`
- `GET /api/teams/overview`

核心代码逻辑：

```tsx
const recentGames = useApi(() => getRecentGames(), []);
const teamOverview = useApi(() => getTeamOverview(), []);
const kpis = mapKpis(teamOverview.data?.kpis ?? []);
const strengthChart = mapTeamChart(teamOverview.data?.charts[0]?.points);
const games = mapGamesToRows(recentGames.data?.games ?? []);
```

分块解释：

- `useApi(() => getRecentGames(), [])`：页面加载时请求近期比赛；
- `useApi(() => getTeamOverview(), [])`：页面加载时请求球队总览；
- `mapKpis()`：把后端 KPI 转成 `StatCard` 需要的格式；
- `mapTeamChart()`：把球队图表点转成 `ChartCard` 简化图表数据；
- `mapGamesToRows()`：把比赛列表转成表格行。

KPI 卡片如何生成：

```tsx
{kpis.map((item) => (
  <StatCard key={item.label} {...item} />
))}
```

解释：

- 后端返回 `kpis`；
- 前端格式化；
- 遍历生成多个 `StatCard`。

图表如何生成：

- 使用 `ChartCard`；
- `variant="line"` 时画 SVG 折线；
- 默认画 CSS 柱状图。

当前局限：

- 首页图表是简化图，不是严格坐标轴图；
- 只取前若干个点；
- 更像概览卡片，不适合精确读数。

### 2. 近期比赛页面

文件：

- `frontend/src/pages/Games.tsx`

页面作用：

- 显示今日赛程、近期比赛和焦点比赛；
- 提供进入单场复盘的入口。

使用数据：

- `getTodayGames()`
- `getRecentGames()`
- `getFocusGames()`

后端对应：

- `GET /api/games/today`
- `GET /api/games/recent`
- `GET /api/games/focus`

比赛数据如何读取：

- 今日比赛从 `nba_client.get_today_scoreboard()` 读取 NBA live scoreboard；
- 近期比赛从 `nba_client.get_league_game_log()` 读取 league game log；
- 焦点比赛在 `game_service.get_focus_games()` 中生成。

今日焦点比赛如何筛选：

文件：`backend/app/services/game_service.py`

核心逻辑：

```text
先取今日比赛
  如果今日没有比赛，则取最近 14 天比赛
  提取双方 team_id
  计算双方最近若干场胜场数
  根据信号计算 focus_score
  按 focus_score 降序排序
```

`_focus_score()` 使用的信号：

- 今日比赛基础分；
- 双方胜率是否接近；
- 双方近期胜场数；
- 如果数据不足，给出保守原因。

比赛复盘和走势分析如何实现：

- Games 页面只是列表和入口；
- 真正复盘在 `/games/:gameId` 的 `GameDetail.tsx`；
- 后端 `get_game_review()` 读取逐回合和 box score；
- `game_flow.py` 构造比分走势和关键节点。

可能存在的局限：

- 焦点分是启发式规则，不是机器学习模型；
- 今日比赛依赖 live scoreboard，外部 API 不稳定会导致为空；
- 如果 `game_id` 对应的 play-by-play 不可用，复盘页数据会不完整。

### 3. 球员分析页面

文件：

- `frontend/src/pages/Players.tsx`

页面作用：

- 查看球员基础数据榜单；
- 选择球员；
- 查看球员高级数据、联盟对比和能力雷达图。

使用数据：

- `getPlayerLeaderboard()`
- `getPlayerProfile()`
- `getPlayerRadar()`

后端对应：

- `GET /api/players/leaderboard`
- `GET /api/players/{player_id}/profile`
- `GET /api/players/{player_id}/radar`

球员基础数据榜单如何生成：

文件：`backend/app/services/player_service.py`

核心函数：

- `get_player_leaderboard()`

流程：

```text
读取 Base 球员数据
  -> 检查 stat 是否支持
  -> 转换 GP、MIN、排序字段为数值
  -> 按 min_gp、min_min 过滤
  -> 可选按 team_abbr 过滤
  -> 按指定 stat 降序排序
  -> 转为 PlayerLeaderboardEntry 列表
```

支持排序字段：

```python
SUPPORTED_LEADERBOARD_STATS = {
    "PTS", "REB", "AST", "STL", "BLK",
    "FG_PCT", "FG3_PCT", "FT_PCT", "PLUS_MINUS",
}
```

球员高级数据如何计算：

高级数据主要来自 NBA API 的 `measure_type="Advanced"`，不是项目自己从基础数据推公式计算。项目负责：

- 读取高级数据；
- 筛选球员；
- 计算联盟平均值；
- 计算百分位排名；
- 组装 `league_comparison`。

核心函数：

- `_metric_comparison()`

逻辑：

```text
某指标所有球员值
  -> 当前球员值
  -> 联盟平均值
  -> pandas rank(pct=True)
  -> 百分位排名
```

注意：

- `DEF_RATING` 是越低越好，所以它在排名时使用反向逻辑。

球员能力雷达图如何生成：

后端：

- `player_service.get_player_radar()`
- `normalization.build_player_radar_scores()`

前端：

- `Players.tsx`
- `charts/RadarChart.tsx`

雷达图维度：

文件：`backend/app/analytics/normalization.py`

```python
RADAR_DIMENSIONS = {
    "scoring": [("PTS", False), ("TS_PCT", False), ("USG_PCT", False)],
    "playmaking": [("AST", False), ("AST_PCT", False)],
    "rebounding": [("REB", False), ("REB_PCT", False)],
    "defense": [("STL", False), ("BLK", False), ("DEF_RATING", True)],
    "shooting": [("FG3_PCT", False), ("EFG_PCT", False)],
    "impact": [("NET_RATING", False), ("PIE", False)],
}
```

解释：

- `scoring`：得分、真实命中率、使用率；
- `playmaking`：助攻和助攻率；
- `rebounding`：篮板和篮板率；
- `defense`：抢断、盖帽、防守效率；
- `shooting`：三分命中率、有效命中率；
- `impact`：净效率、PIE。

归一化逻辑：

```python
normalized = ((value - min_value) / (max_value - min_value)) * 100
```

如果 `reverse=True`：

```python
normalized = 100 - normalized
```

含义：

- 普通指标越高越好；
- `DEF_RATING` 越低越好，所以反向处理；
- 所有指标变成 0-100 分；
- 一个维度下多个指标取平均。

切换球员后页面如何更新：

前端状态：

```tsx
const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
```

当选择框变化：

```tsx
onChange={(event) => setSelectedPlayerId(Number(event.target.value) || null)}
```

然后：

- `activePlayerId` 更新；
- `useApi()` 依赖 `[activePlayerId, season]` 变化；
- 重新请求 profile；
- `useApi()` 依赖 `[activePlayerId, season, minGp, minMin]` 变化；
- 重新请求 radar；
- 页面自动重新渲染。

### 4. 球队分析页面

文件：

- `frontend/src/pages/Teams.tsx`

页面作用：

- 选择球队和赛季；
- 展示该球队进攻、防守、净效率、节奏；
- 展示进攻/防守拆解；
- 用攻防象限图比较联盟球队差异。

使用数据：

- `getTeamOverview()`
- `getTeamOffense()`
- `getTeamDefense()`

后端对应：

- `GET /api/teams/overview`
- `GET /api/teams/offense`
- `GET /api/teams/defense`

球队综合表现如何计算：

文件：`backend/app/services/team_service.py`

核心流程：

```text
Base 球队数据
  + Advanced 球队数据
  + Four Factors 球队数据
  + Opponent 球队数据
  + Defense 球队数据
  -> 按 TEAM_ID 合并
  -> 统一字段别名
  -> 生成 KPI、表格、图表点
```

核心函数：

- `_merge_stats()`
- `_prepared_rows()`
- `get_team_overview()`
- `get_team_offense()`
- `get_team_defense()`

进攻效率、防守效率、净效率如何得到：

- `OFF_RATING`、`DEF_RATING`、`NET_RATING` 主要来自 NBA API 的 Advanced 统计；
- 项目在 `_metric_value()` 中处理字段别名，例如 `OFF_RATING` 可能来自 `OFF_RATING` 或 `OFF_RATING_ADV`；
- 项目本身不从 play-by-play 手动计算 ORtg/DRtg。

图表如何展示球队差异：

前端 `Teams.tsx` 中的 `EfficiencyQuadrant`：

- x 轴：进攻效率 `off_rating`；
- y 轴：防守效率 `def_rating`；
- 每个点是一支球队；
- 平均线把图切成四个象限；
- 选中的球队点更大、更突出。

注意：

- 防守效率越低越好；
- 图上 y 值的解释要讲清楚，否则老师容易误会“越高越好”。

### 5. 投篮分析页面

文件：

- `frontend/src/pages/Shots.tsx`

页面作用：

- 支持按球员或球队查看投篮；
- 展示 Shot Chart；
- 展示投篮热区；
- 展示命中率分布和高效区域表。

使用数据：

- 球员选项：`getPlayerLeaderboard()`
- 球队选项：`getTeamOverview()`
- 球员投篮：`getPlayerShotChart()`、`getPlayerShotZones()`
- 球队投篮：`getTeamShotChart()`、`getTeamShotZones()`

投篮热区图 / Shot Chart 如何实现：

后端：

- `nba_client.get_shot_chart_detail()`
- `shot_service.get_player_shot_chart()`
- `shot_service.get_team_shot_chart()`

前端：

- `charts/ShotChart.tsx`
- `charts/HeatMap.tsx`

Shot Chart：

- 使用 `LOC_X`、`LOC_Y`；
- 把 NBA 坐标转换到 SVG 半场坐标；
- 命中显示圆点；
- 未命中显示叉号；
- `<title>` 提供 hover 信息。

关键坐标转换：

```ts
const x = clamp(locX + COURT_WIDTH / 2, 2, COURT_WIDTH - 2);
const y = clamp(COURT_HEIGHT - (locY + BASKET_Y), 2, MAX_Y);
```

解释：

- NBA 的 `LOC_X` 以篮筐中线为 0；
- SVG 坐标从左上角开始；
- 所以 x 要加半场宽度；
- y 要反向映射，让篮筐附近显示在正确位置。

命中率分布如何计算：

文件：`backend/app/analytics/shot_analysis.py`

核心函数：

- `get_shot_zone_summary()`

流程：

```text
按 SHOT_ZONE_BASIC / SHOT_ZONE_AREA / SHOT_ZONE_RANGE 分组
  -> FGA = 出手次数
  -> FGM = 命中次数
  -> POINTS = 命中得分总和
  -> FG_PCT = FGM / FGA
  -> PPS = POINTS / FGA
  -> 按 PPS、FGA 排序
```

高效区域如何识别：

核心函数：

- `identify_high_efficiency_zones()`

逻辑：

```text
先做区域汇总
  -> 过滤 FGA >= min_fga
  -> 根据 PPS 打标签
```

标签规则：

```python
if pps >= 1.20: high
elif pps >= 1.00: normal
else: low
```

球员 Shot Chart 和球队 Shot Chart 的区别：

后端调用同一个 NBA endpoint，但参数不同：

```text
球员：
player_id = 指定球员 ID
team_id = None / 0

球队：
player_id = None / 0
team_id = 指定球队 ID
```

返回结构相同：

- `shots`：每次出手点；
- `zones`：区域汇总；
- `totals`：总出手、总命中、命中率、总得分、PPS。

### 6. 智能问数页面

文件：

- `frontend/src/pages/AskAI.tsx`

页面作用：

- 输入自然语言问题；
- 调用后端 AI 问数接口；
- 展示回答；
- 展示本次回答使用的数据类型标签；
- 支持简单 Markdown 渲染。

用户输入的问题如何处理：

前端：

```tsx
const response = await askAI(trimmedQuestion);
```

`askAI()`：

```ts
return request<AskAiResponse>("/api/ai/ask", {
  method: "POST",
  body: JSON.stringify({ question }),
});
```

后端：

- `backend/app/api/ai.py`
- `backend/app/services/query_service.py`

后端流程：

```text
POST /api/ai/ask
  -> ask_ai(payload)
  -> ask_question(payload.question)
  -> classify_question(question)
  -> query_structured_data(classification)
  -> answer_question(question, context_data)
  -> 返回 answer + intent + entities + data
```

是否调用大模型 API：

是。两个环节可能调用：

1. `classify_question()`：让模型把自然语言问题分类成 JSON；
2. `answer_question()`：把分类结果和结构化数据发给模型，让模型生成中文分析。

如果未配置：

- `ai_service.chat()` 会返回 `UNCONFIGURED_MESSAGE`；
- 分类 JSON 解析失败后会降级为 `unknown`；
- 页面会提示 AI 未配置。

Prompt 在哪里构造：

- 文件：`backend/app/services/ai_service.py`
- 函数：
  - `_system_prompt()`
  - `_data_message()`
  - `generate_game_report()`
  - `generate_player_report()`
  - `generate_team_report()`
  - `answer_question()`

数据上下文如何传给模型：

```python
answer_question(
    question,
    {
        "classification": classification,
        "data": _jsonable(structured_data),
    },
)
```

然后 `_data_message()` 把数据转成 JSON 字符串，放进用户消息。

模型回答如何展示：

- 后端返回 `AskAIResponse`；
- 前端把 `answer` 放进 `MarkdownCard`；
- `MarkdownCard` 支持标题、列表、加粗、行内代码。

API 调用失败如何处理：

后端：

- `ai_service.chat()` 捕获 `requests.RequestException`；
- 抛出 `AIServiceError`；
- `api/ai.py` 捕获后返回 HTTP 502。

前端：

- `AskAI.tsx` 捕获错误；
- 设置 `error`；
- 如果是 502 或包含 API key/LLM 相关文本，则显示配置提示。

---

## 六、核心函数和核心组件讲解

### 1. `get_settings()`

所在文件：

- `backend/app/core/config.py`

作用：

- 读取并缓存项目配置。

参数：

- 无。

返回值：

- `Settings` 对象。

调用位置：

- `main.py`
- `cache.py`
- `nba_client.py`
- `ai_service.py`
- `database.py`
- `export_demo_data.py`

为什么重要：

- 它决定缓存目录、demo 模式、LLM API 配置等。

容易误解：

- `.env` 文件读取路径与启动目录有关。通常从 `backend` 目录启动时能正确读取 `backend/.env`。

### 2. `_get_cached_dataframe()`

所在文件：

- `backend/app/services/nba_client.py`

作用：

- 统一读取 DataFrame 类型数据；
- 优先 demo 数据，其次本地缓存，最后 NBA API。

参数：

- `endpoint`：接口名；
- `params`：请求参数；
- `ttl_seconds`：缓存有效期；
- `fetcher`：真正请求 API 的函数。

返回值：

- 成功：`pd.DataFrame`
- 失败：结构化错误 dict，例如 `{"ok": False, ...}`

调用位置：

- `get_league_game_log()`
- `get_player_stats()`
- `get_team_stats()`
- `get_shot_chart_detail()`
- `get_play_by_play()`
- `get_box_score_traditional()`

为什么重要：

- 它是后端数据稳定性的关键。

容易误解：

- 它不一定总返回 DataFrame，所以 service 层必须判断是否是错误 payload。

### 3. `get_recent_games()`

所在文件：

- `backend/app/services/game_service.py`

作用：

- 获取某赛季最近若干天的比赛。

参数：

- `season`：赛季；
- `days`：天数，默认 7。

返回值：

- `RecentGamesResponse`

调用位置：

- `backend/app/api/games.py`
- 前端 `Dashboard.tsx`、`Games.tsx`

为什么重要：

- 它是首页和近期比赛页的基础数据。

容易误解：

- “最近”不是今天往前算，而是以数据中最新比赛日期为基准往前取。

### 4. `get_game_review()`

所在文件：

- `backend/app/services/game_service.py`

作用：

- 生成单场比赛复盘数据。

参数：

- `game_id`：比赛 ID。

返回值：

- `GameReviewResponse`

内部调用：

- `nba_client.get_play_by_play()`
- `build_game_flow()`
- `summarize_game_flow()`
- `detect_key_moments()`
- `nba_client.get_box_score_traditional()`
- `_team_comparison()`
- `_top_players()`

为什么重要：

- 单场比赛复盘是项目分析深度最高的模块之一。

容易误解：

- 如果没有逐回合数据，它不能凭最终比分生成完整走势。

### 5. `build_game_flow()`

所在文件：

- `backend/app/analytics/game_flow.py`

作用：

- 从 play-by-play 数据构造比分时间线。

参数：

- `play_by_play_df`：逐回合 DataFrame。

返回值：

- DataFrame，包含：
  - `period`
  - `game_clock`
  - `home_score`
  - `away_score`
  - `score_margin`
  - `clock_seconds`

调用位置：

- `game_service.get_game_review()`

为什么重要：

- 前端 `GameFlowChart` 的数据就来自这里。

容易误解：

- 原始 play-by-play 不是天然折线图，需要先解析比分字段和分差字段。

### 6. `detect_key_moments()`

所在文件：

- `backend/app/analytics/game_flow.py`

作用：

- 从比分走势中识别关键节点。

识别内容：

- 最大领先；
- 领先变化；
- 连续得分高潮；
- 第四节最后 5 分钟关键得分。

返回值：

- list of dict。

调用位置：

- `game_service.get_game_review()`

为什么重要：

- 把普通折线变成有解释价值的比赛复盘。

容易误解：

- 这是基于规则的识别，不是 AI 自动发现。

### 7. `get_player_leaderboard()`

所在文件：

- `backend/app/services/player_service.py`

作用：

- 生成球员基础数据榜单。

参数：

- `season`
- `stat`
- `min_gp`
- `min_min`
- `team_abbr`

返回值：

- `PlayerLeaderboardResponse`

调用位置：

- `api/players.py`
- `Players.tsx`
- `Shots.tsx` 用它获取球员选项。

为什么重要：

- 是球员分析和投篮分析中选择球员的基础。

容易误解：

- 它展示的是 Base 数据；高级数据来自另一个接口。

### 8. `build_player_radar_scores()`

所在文件：

- `backend/app/analytics/normalization.py`

作用：

- 计算球员雷达图六个维度分数。

参数：

- `player_df`
- `player_id`
- `min_gp`
- `min_min`

返回值：

- dict，包含球员基础信息和 `radar` 列表。

调用位置：

- `player_service.get_player_radar()`

为什么重要：

- 这是球员分析页最有“分析感”的代码。

容易误解：

- 雷达图分数不是 NBA 官方分数，而是项目基于当前样本做的 min-max 归一化。

### 9. `get_team_overview()`

所在文件：

- `backend/app/services/team_service.py`

作用：

- 生成球队总览：联盟 KPI、球队排名表、图表点。

参数：

- `season`

返回值：

- `TeamModuleResponse`

调用位置：

- `api/teams.py`
- `Dashboard.tsx`
- `Teams.tsx`
- `Shots.tsx` 用它获取球队选项。

为什么重要：

- 首页和球队分析页都依赖它。

容易误解：

- 它没有自己计算所有高级指标，而是合并 NBA API 多个 measure_type 的结果。

### 10. `get_shot_zone_summary()`

所在文件：

- `backend/app/analytics/shot_analysis.py`

作用：

- 按投篮区域聚合出手、命中和效率。

参数：

- `df`：投篮 DataFrame。

返回值：

- DataFrame，包含 `FGA`、`FGM`、`FG_PCT`、`POINTS`、`PPS`。

调用位置：

- `shot_service.get_player_shot_chart()`
- `shot_service.get_team_shot_chart()`
- `shot_service.get_player_shot_zones()`
- `shot_service.get_team_shot_zones()`

为什么重要：

- 投篮热区和高效区域分析都基于它。

容易误解：

- `FG_PCT` 只看命中率，`PPS` 更能体现 3 分球价值。

### 11. `identify_high_efficiency_zones()`

所在文件：

- `backend/app/analytics/shot_analysis.py`

作用：

- 按 PPS 给区域打高效/常规/低效标签。

参数：

- `df`
- `min_fga`

返回值：

- 带 `efficiency_level` 的区域 DataFrame。

为什么重要：

- 它让投篮分析不只是展示坐标，还能给出分析结论。

容易误解：

- 出手太少的区域会被过滤，否则小样本容易误导。

### 12. `chat()`

所在文件：

- `backend/app/services/ai_service.py`

作用：

- 调用兼容 OpenAI 的 Chat Completions API。

参数：

- `messages`
- `temperature`

返回值：

- 模型回复文本。

调用位置：

- `generate_game_report()`
- `generate_player_report()`
- `generate_team_report()`
- `answer_question()`
- `query_service.classify_question()` 间接导入使用。

为什么重要：

- 所有 AI 能力最终都通过它访问模型。

容易误解：

- 它不是 OpenAI 官方 SDK，而是直接用 `requests.post()` 调 HTTP。

### 13. `ask_question()`

所在文件：

- `backend/app/services/query_service.py`

作用：

- 智能问数的总控函数。

参数：

- `question`

返回值：

- dict，包含：
  - `answer`
  - `intent`
  - `entities`
  - `need_data`
  - `data`

调用位置：

- `api/ai.py` 的 `ask_ai()`

为什么重要：

- 它把“自然语言 -> 意图识别 -> 数据查询 -> 模型回答”串起来。

容易误解：

- 当前不是数据库 SQL Agent，也不是完全自动分析全量数据，而是先分类，再调用固定 service 接口。

### 14. `useApi()`

所在文件：

- `frontend/src/api/client.ts`

作用：

- 前端统一管理异步请求状态。

参数：

- `loader`：返回 Promise 的请求函数；
- `deps`：React effect 依赖数组。

返回值：

```ts
{
  data,
  loading,
  error
}
```

调用位置：

- 所有主要页面。

为什么重要：

- 它避免每个页面重复写 loading/error/data 状态。

容易误解：

- `deps` 变化时会重新请求，所以切换赛季、球员、球队时页面自动刷新。

### 15. `ShotChart`

所在文件：

- `frontend/src/charts/ShotChart.tsx`

作用：

- 把投篮点画在半场图上。

参数：

- `shots`
- `title`

返回值：

- React SVG 组件。

调用位置：

- `Shots.tsx`

为什么重要：

- 它是投篮空间分析的核心可视化。

### 16. `RadarChart`

所在文件：

- `frontend/src/charts/RadarChart.tsx`

作用：

- 把后端的 0-100 雷达分数画成多边形。

参数：

- `data`
- `title`

为什么重要：

- 它把多维高级指标转成直观球员画像。

---

## 七、关键指标解释

| 指标 | 中文含义 | 代码字段 | 原始/计算 | 项目中展示 | 篮球分析意义 |
|---|---|---|---|---|---|
| PTS | 得分 | `PTS` / `pts` / `points` | 多数来自 NBA API；单场 team comparison 中由 box score 汇总 | 球员榜单、比赛复盘、投篮总得分 | 最直接的产量指标，但要结合效率看 |
| REB | 篮板 | `REB` / `reb` / `rebounds` | NBA API 原始字段或 box score 汇总 | 球员榜单、比赛复盘 | 体现争抢球权和终结防守回合能力 |
| AST | 助攻 | `AST` / `ast` / `assists` | NBA API 原始字段或 box score 汇总 | 球员榜单、比赛复盘 | 体现组织和带动队友能力 |
| STL | 抢断 | `STL` / `stl` / `steals` | NBA API 原始字段或 box score 汇总 | 球员榜单、比赛复盘 | 体现防守侵略性和预判 |
| BLK | 盖帽 | `BLK` / `blk` / `blocks` | NBA API 原始字段或 box score 汇总 | 球员榜单、比赛复盘 | 体现护筐和干扰投篮能力 |
| TOV | 失误 | `TOV`，单场也兼容 `TO` | NBA API 原始字段或 box score 汇总 | 比赛复盘球队对比、指标解释 | 失误越多，进攻回合损耗越高 |
| FG% | 投篮命中率 | `FG_PCT` / `fg_pct` | NBA API 原始字段；投篮区域中由 `FGM/FGA` 计算 | 球员榜单、比赛复盘、投篮区域 | 衡量总体投篮准确性 |
| 3P% | 三分命中率 | `FG3_PCT` / `fg3_pct` | NBA API 原始字段 | 球员榜单、比赛复盘、雷达图 shooting 维度 | 衡量外线投射效率 |
| FT% | 罚球命中率 | `FT_PCT` / `ft_pct` | NBA API 原始字段 | 球员榜单、指标解释 | 衡量罚球稳定性 |
| USG% | 使用率 | `USG_PCT` | NBA API Advanced 原始字段 | 球员高级数据、球员 KPI、雷达图 scoring 维度 | 衡量球员终结回合的占比 |
| TS% | 真实命中率 | `TS_PCT` | NBA API Advanced 原始字段 | 球员高级数据、球员 KPI、雷达图 scoring 维度 | 综合考虑 2 分、3 分和罚球的得分效率 |
| eFG% | 有效命中率 | `EFG_PCT` | NBA API 原始字段；球队 Four Factors 中读取 | 球员高级数据、球队进攻、雷达图 shooting 维度 | 把三分额外价值计入投篮效率 |
| ORtg | 进攻效率 | `OFF_RATING` / `off_rating` | NBA API Advanced 原始字段 | 球队页、球员高级数据、首页 KPI | 每 100 回合得分，剔除节奏影响 |
| DRtg | 防守效率 | `DEF_RATING` / `def_rating` | NBA API Advanced 原始字段 | 球队页、球员高级数据、雷达图 defense 维度 | 每 100 回合失分，越低越好 |
| Net Rating | 净效率 | `NET_RATING` / `net_rating` | NBA API Advanced 原始字段 | 球队页、球员高级数据、首页、雷达图 impact 维度 | 每 100 回合净胜分，综合攻防强弱 |
| Pace | 比赛节奏 | `PACE` / `pace` | NBA API Advanced 原始字段 | 球队页、首页 KPI、球员高级数据 | 每 48 分钟估算回合数，反映比赛速度 |

补充指标：

- `PPS`：每次出手得分，项目在 `shot_analysis.py` 中计算，公式是 `POINTS / FGA`。
- `PIE`：比赛影响力指数，来自 NBA Advanced 数据，用于雷达图 impact 维度。
- `AST_PCT`：助攻率，来自 Advanced 数据，用于组织维度。
- `REB_PCT`：篮板率，来自 Advanced 数据，用于篮板维度。

---

## 八、可视化代码讲解

### 1. 使用了什么可视化库

项目没有使用 ECharts、Recharts、Plotly 等可视化库，而是主要使用：

- React 组件；
- SVG；
- CSS。

好处：

- 依赖少；
- 可控性高；
- 适合作为课程项目展示“自己实现了图表”。

不足：

- 坐标轴、tooltip、缩放、图例等能力需要自己维护；
- 精确交互和复杂图表不如成熟图表库。

### 2. `ChartCard`

文件：

- `frontend/src/components/ChartCard.tsx`

用于：

- 首页简化折线图；
- 首页简化柱状图。

数据来源：

- `Dashboard.tsx` 中的 `mapTeamChart()`。

字段含义：

- `label`：x 轴或柱子标签；
- `value`：柱高或折线 y 值。

实现方式：

- 折线：计算每个点的 x/y，用 SVG `<polyline>` 连接；
- 柱状：用 CSS 设置 `height`。

适合答辩展示：

- 可以简单展示首页概览，但不要把它当作最核心图表。

### 3. `GameFlowChart`

文件：

- `frontend/src/charts/GameFlowChart.tsx`

数据来源：

- 后端 `get_game_review()` 返回的 `game_flow` 和 `key_moments`。

x 轴代表：

- 比赛已经进行的时间；
- 由 `period + game_clock` 转换得到。

y 轴代表：

- `score_margin` 分差；
- 正数表示主队领先；
- 负数表示客队领先。

颜色：

- 折线使用蓝紫渐变；
- 鼠标悬停点会高亮。

hover 信息：

- 通过 React 状态 `activeIndex` 控制；
- 显示时间、比分、分差和事件说明。

适合答辩重点展示：

- 非常适合。它能说明项目不是只展示最终比分，而是在分析比赛过程。

### 4. `RadarChart`

文件：

- `frontend/src/charts/RadarChart.tsx`

数据来源：

- `GET /api/players/{player_id}/radar`
- 后端 `build_player_radar_scores()`。

轴代表：

- 得分；
- 投射；
- 组织；
- 篮板；
- 防守；
- 影响力。

实现方式：

- `polarPoint()` 把维度和分数转换成极坐标点；
- 多个点用 SVG `<polygon>` 连起来；
- 环线代表 20、40、60、80、100 分。

适合答辩重点展示：

- 非常适合。它能讲清楚“多指标归一化”和“球员画像”。

### 5. `ShotChart`

文件：

- `frontend/src/charts/ShotChart.tsx`

数据来源：

- `GET /api/shots/player/{player_id}`
- `GET /api/shots/team/{team_id}`

x 轴 / y 轴：

- x：`LOC_X` 转 SVG 横坐标；
- y：`LOC_Y` 转 SVG 纵坐标。

颜色/形状：

- 命中：圆点；
- 未命中：叉号。

hover 信息：

- `<title>` 显示命中/未命中、区域、距离、动作类型。

适合答辩重点展示：

- 非常适合。它把篮球场空间和数据结合起来，展示效果强。

### 6. `HeatMap`

文件：

- `frontend/src/charts/HeatMap.tsx`

数据来源：

- `GET /api/shots/player/{player_id}/zones`
- `GET /api/shots/team/{team_id}/zones`

区域颜色代表：

- `high`：高效区域；
- `normal`：常规区域；
- `low`：低效区域；
- empty：无数据。

核心实现：

- 预定义若干半场区域形状；
- 根据 `SHOT_ZONE_BASIC` 找到后端汇总区域；
- 根据 `efficiency_level` 选择 CSS class。

适合答辩重点展示：

- 适合和 Shot Chart 一起讲，强调“从点到区域”的分析过程。

### 7. `EfficiencyQuadrant`

文件：

- `frontend/src/pages/Teams.tsx`

数据来源：

- `getTeamOverview()` 返回的球队表格。

x 轴：

- 进攻效率 `off_rating`。

y 轴：

- 防守效率 `def_rating`。

注意：

- 防守效率越低越好；
- 需要在答辩时解释图中位置的含义。

适合答辩重点展示：

- 适合展示球队之间的差异。

---

## 九、AI 智能问数实现讲解

### 1. API 配置在哪里

配置文件：

- `backend/app/core/config.py`
- `backend/.env.example`

配置项：

```env
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

调用文件：

- `backend/app/services/ai_service.py`

### 2. 模型厂商如何切换

当前实现使用的是“OpenAI-compatible”接口，只要厂商支持 Chat Completions 兼容格式，就可以通过修改：

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

切换模型。

当前 `LLM_PROVIDER` 只是配置字段，代码里没有复杂 provider 分支。

### 3. Prompt 模板在哪里

文件：

- `backend/app/services/ai_service.py`

核心函数：

- `_system_prompt(task)`
- `_data_message(title, data, extra_instruction)`

Prompt 规则大意：

- 你是严谨的篮球数据分析助手；
- 只能基于传入数据分析；
- 不要编造数据中不存在的事实；
- 数据不足要明确说明；
- 输出中文；
- 结构清晰。

### 4. 用户问题如何和数据拼接

文件：

- `backend/app/services/query_service.py`

流程：

```text
用户问题
  -> classify_question() 识别 intent 和 entities
  -> query_structured_data() 调用固定业务接口
  -> answer_question(question, {"classification": ..., "data": ...})
  -> ai_service._data_message() 把 context_data 转成 JSON
  -> 发送给模型
```

### 5. 是否有安全限制或异常处理

有基础限制：

- system prompt 要求模型只能基于传入数据回答；
- 数据不足时说明不足；
- 不要编造。

异常处理：

- 未配置 API 时返回未配置提示；
- HTTP 请求失败抛 `AIServiceError`；
- API 层转成 502；
- 前端显示错误或配置提示。

不足：

- 没有复杂 prompt injection 防护；
- 没有对用户问题做安全过滤；
- 没有模型输出校验；
- 没有引用级证据定位。

### 6. 当前实现是“真正基于数据回答”吗

更准确地说：

> 当前实现是“先用 LLM 做意图识别，再调用固定后端数据接口拿到结构化数据，最后把数据摘要传给模型生成分析”。

它不是：

- 直接让模型访问数据库；
- 让模型执行 SQL；
- 模型自行抓取数据；
- 完全确定性的问答系统。

它的优点：

- 不让模型凭空找数据；
- 数据来自后端结构化接口；
- 问答和业务接口结合，可信度比纯聊天高。

它的局限：

- 分类错了，后续数据就会错；
- 实体识别依赖模型；
- 传给模型的数据可能不够完整；
- 模型回答仍可能有表达性偏差。

### 7. 后续如何优化成更可靠的数据问答系统

可以从五方面优化：

1. 增加确定性实体解析：
   - 球员名、球队名建立本地字典；
   - 中文别名映射到官方英文名或 ID。

2. 增加工具调用式问答：
   - 让模型只能选择后端定义好的工具；
   - 工具参数用 JSON Schema 验证。

3. 增加数据引用：
   - 每个回答附带“使用了哪些接口、哪些字段、哪些行”。

4. 增加规则型 fallback：
   - 常见问题如“谁得分最高”可以不用 LLM，直接 pandas 排序回答。

5. 增加输出校验：
   - 检查回答中的球员名、球队名、数值是否存在于传入数据。

---

## 十、代码中的设计优点

### 1. 前后端分离清晰

后端负责数据获取、处理和接口；
前端负责展示和交互；
两者通过 JSON API 通信。

优点：

- 职责清楚；
- 方便独立调试；
- 适合扩展移动端或其他前端。

### 2. 后端分层结构清楚

结构大致是：

```text
api -> services -> analytics / nba_client -> schemas
```

优点：

- API 层不堆大量 pandas 逻辑；
- 分析函数可以单独测试；
- Pydantic 模型保证输出结构稳定。

### 3. 有缓存和 demo 模式设计

`nba_client.py` 支持：

- 先读 demo 文件；
- 再读缓存；
- 最后请求 NBA API。

优点：

- 适合课堂答辩；
- 降低外部 API 不稳定风险；
- 提升响应速度。

### 4. 数据处理和可视化结合较完整

项目不是只做表格，还包括：

- 比赛走势；
- 关键节点；
- 球员雷达图；
- 球队攻防象限；
- Shot Chart；
- 投篮热区。

这让项目更有产品感和分析深度。

### 5. TypeScript 类型比较完整

`frontend/src/api/client.ts` 中定义了大量响应类型。

优点：

- 前端开发时字段更明确；
- 减少拼错字段的问题；
- 有助于初学者理解接口结构。

### 6. 有测试覆盖

`backend/tests/` 覆盖了：

- 缓存；
- demo 数据读取；
- 比赛走势；
- 球员服务；
- 球队服务；
- 投篮分析；
- AI 未配置场景。

这在课程项目中是加分点。

### 7. AI 模块没有直接裸聊

智能问数不是简单把用户问题丢给模型，而是：

- 先识别意图；
- 再查询结构化数据；
- 再把数据传给模型。

这比普通 Chatbot 更贴近“数据问答”。

---

## 十一、代码中的问题和改进建议

### 1. 中文文案存在编码风险

问题位置：

- `README.md`
- `docs/demo_script.md`
- `frontend/src/constants/zhLabels.ts`
- 多个前端页面和后端中文提示。

为什么是问题：

- 当前终端读取时大量中文显示为乱码；
- 如果源码实际已乱码，页面和 API 提示也可能乱码。

影响：

- 答辩展示观感受影响；
- 后续维护难以理解文案；
- 表格列名和 tooltip 可能显示异常。

后续如何改：

- 统一文件编码为 UTF-8；
- 检查编辑器保存格式；
- 对已损坏中文重新恢复；
- 在 CI 中加编码检查或至少人工检查页面显示。

### 2. 多处 `_safe_int` / `_safe_float` 重复

问题位置：

- `game_service.py`
- `player_service.py`
- `team_service.py`
- `shot_service.py`

为什么是问题：

- 逻辑重复；
- 将来修复一个转换问题时需要改多个文件。

影响：

- 维护成本增加；
- 行为可能不一致。

后续如何改：

- 新增 `backend/app/utils/typing.py` 或 `backend/app/core/converters.py`；
- 统一放 `safe_int()`、`safe_float()`、`safe_date()`。

### 3. 数据字段硬编码较多

问题位置：

- `player_service.py` 的字段列表；
- `team_service.py` 的 `_metric_value()` aliases；
- `shot_service.py` 的 `SHOT_COLUMNS`；
- 前端 `Teams.tsx`、`Players.tsx` 的指标列表。

为什么是问题：

- NBA API 字段变化时容易出错；
- 增加指标需要多处修改。

影响：

- 扩展性变差；
- 调试成本高。

后续如何改：

- 把指标配置集中到配置文件或常量模块；
- 后端和前端共享字段文档；
- 对缺字段场景提供更明确日志。

### 4. `context_data` 请求字段当前没有被使用

问题位置：

- `backend/app/schemas/ai.py` 中 `AskAIRequest` 有 `context_data`；
- `backend/app/api/ai.py` 的 `ask_ai()` 只调用 `ask_question(payload.question)`。

为什么是问题：

- 请求模型支持上下文，但实际忽略；
- 前端或未来调用方以为能传上下文，实际无效。

影响：

- 接口语义不一致；
- 后续扩展时容易误判。

后续如何改：

- 要么删除 `context_data`；
- 要么在 `ask_question()` 中合并用户上下文；
- 明确哪些上下文可信、哪些只是用户补充。

### 5. SQLite 配置存在，但业务主线未使用

问题位置：

- `backend/app/db/database.py`
- `DATABASE_URL` 配置。

为什么是问题：

- README 提到 SQLite，但当前主要缓存是 JSON 文件；
- 容易让老师追问数据库到底有没有用。

影响：

- 架构说明和代码现状略不一致。

后续如何改：

- 如果不用数据库，说明它是预留；
- 如果要使用，补充表模型和数据落库逻辑；
- README 中明确“当前缓存主要是文件缓存，SQLite 为预留扩展”。

### 6. demo 数据目录当前为空

问题位置：

- `data/processed/`

为什么是问题：

- `DEMO_MODE=true` 时依赖这里的 CSV/JSON；
- 当前扫描为空。

影响：

- 如果答辩时开启 demo 模式，可能没有数据；
- 需要先运行 `scripts/export_demo_data.py`。

后续如何改：

- 准备一套固定 demo 数据；
- 在 README 中说明如何生成；
- 答辩前确认 `data/processed` 有完整文件。

### 7. 前端默认赛季硬编码

问题位置：

- `frontend/src/api/client.ts` 的 `DEFAULT_SEASON = "2025-26"`；
- 多个页面的 `SEASONS` 数组。

为什么是问题：

- 新赛季开始后需要手动改代码；
- 页面默认值可能和后端当前赛季逻辑不一致。

影响：

- 数据为空；
- 用户体验不稳定。

后续如何改：

- 后端提供 `/api/config` 或 `/api/seasons`；
- 前端从后端读取默认赛季和可用赛季。

### 8. AI 问数依赖 LLM 做意图分类

问题位置：

- `query_service.classify_question()`

为什么是问题：

- LLM 未配置时分类失败；
- LLM 分类不稳定；
- 对实体名识别不一定准确。

影响：

- 问数回答可能不稳定；
- 中文别名可能识别错。

后续如何改：

- 为球队/球员建立本地词典；
- 常见问题用规则解析；
- 分类结果加置信度和二次确认。

### 9. 图表配置和 SVG 逻辑较分散

问题位置：

- `GameFlowChart.tsx`
- `RadarChart.tsx`
- `ShotChart.tsx`
- `HeatMap.tsx`
- `Teams.tsx` 中的 `EfficiencyQuadrant`

为什么是问题：

- 每张图都自己处理坐标、tooltip、颜色；
- 统一风格和交互比较困难。

影响：

- 后续增加图表成本较高；
- 可访问性和响应式适配需要逐个维护。

后续如何改：

- 抽出图表通用工具；
- 或引入 ECharts/Recharts；
- 保留 Shot Chart 这种特殊图为自定义 SVG。

### 10. 外部 API 异常提示可以更细

问题位置：

- `nba_client.py`
- 各 service 的错误降级。

为什么是问题：

- 当前多数失败会返回空列表或通用提示；
- 用户不知道是网络问题、参数问题还是数据本身为空。

影响：

- 调试困难；
- 答辩现场不易解释空数据。

后续如何改：

- API 返回错误码和错误来源；
- 前端区分“暂无数据”和“数据源失败”；
- 后端日志记录 endpoint 和参数。

### 11. 球员雷达图使用 min-max，受样本影响较大

问题位置：

- `normalization.min_max_normalize()`

为什么是问题：

- 样本范围变化会导致同一球员分数变化；
- 极端值会压缩大多数球员分数。

影响：

- 雷达图更适合相对比较，不是绝对能力评分。

后续如何改：

- 使用百分位排名；
- 使用固定联盟基准；
- 按位置分组归一化。

---

## 十二、答辩讲解稿

各位老师好，我的项目叫 Hoop Insight，是一个篮球数据分析和智能问数平台。选择篮球数据作为主题，是因为篮球比赛天然会产生大量结构化数据，比如得分、篮板、助攻、投篮位置、比赛时间和球队效率等。单看这些原始数字其实不够直观，所以我希望通过这个项目，把数据读取、指标计算、可视化展示和 AI 分析结合起来，帮助用户更快理解比赛、球员和球队表现。

系统整体采用前后端分离架构。后端使用 Python 和 FastAPI，负责从 NBA 相关接口读取数据，并通过本地缓存和 demo 数据机制提高稳定性。后端还使用 pandas 对数据进行筛选、聚合和指标计算，比如比赛走势、投篮区域效率、球员雷达图分数等。前端使用 React、TypeScript 和 Vite，提供数据总览、近期比赛、球员分析、球队分析、投篮分析和智能问数六个主要模块。

在功能上，首页会展示球队效率 KPI、近期比赛和整体概览。近期比赛页面可以查看今日比赛、焦点比赛和最近比赛，并进入单场复盘。单场复盘会根据逐回合数据生成比分走势，提取最大领先、领先变化、得分高潮等关键节点。球员分析页面提供基础数据榜单、高级指标对比和能力雷达图。球队分析页面从进攻效率、防守效率、净效率和节奏等角度分析球队。投篮分析页面则通过 Shot Chart 和热区图展示球员或球队的出手空间分布和高效区域。

项目的一个重点是数据流设计。原始数据首先由 `nba_client.py` 统一获取，它会优先读取 demo 数据，其次读取本地缓存，最后才调用 NBA API。然后 service 层把 DataFrame 转换成页面需要的结构，analytics 层负责具体分析算法，schemas 层定义接口返回格式。前端再通过统一的 `client.ts` 请求接口，用 KPI 卡片、表格和 SVG 图表展示结果。

智能问数部分接入了兼容 OpenAI Chat Completions 的大模型接口。用户输入自然语言问题后，后端会先让模型识别问题意图和实体，比如是问球员、球队、比赛还是投篮；然后调用对应的结构化数据接口；最后把查询到的数据作为上下文传给模型，让模型生成中文分析回答。它不是完全凭空聊天，而是基于后端整理后的数据进行回答。

这个项目的亮点主要有四个：第一，前后端分层比较清晰；第二，不只是展示表格，而是加入了比赛走势、雷达图、攻防象限和投篮热区等分析图表；第三，后端有缓存和 demo 数据机制，适合课堂展示；第四，智能问数把自然语言和结构化篮球数据连接起来，降低了数据分析门槛。

当然，项目还有可以改进的地方。比如外部 NBA API 稳定性会影响实时数据获取，所以需要准备更完整的 demo 数据；部分中文文案存在编码显示风险；AI 问数目前仍依赖模型进行意图识别，准确性还可以通过本地实体词典、规则解析和结果校验继续提升。后续我希望继续扩展数据源、增加预测模型，并把智能问数优化成更可靠的数据问答系统。

---

## 十三、答辩可能被问到的问题

### 1. 为什么选择篮球数据分析？

参考回答：

篮球比赛数据结构化程度高，既有基础数据如得分、篮板、助攻，也有高级数据如真实命中率、进攻效率、防守效率，还有投篮坐标这种空间数据。它很适合展示 Python 数据处理、前端可视化和 AI 问答的综合能力。

### 2. 数据从哪里来？

参考回答：

主要通过 `nba_api` 获取 NBA 官方相关数据，包括赛程、比赛日志、球员统计、球队统计、投篮数据、逐回合数据和 box score。项目还设计了本地 JSON 缓存和 demo 数据目录，降低外部 API 不稳定对展示的影响。

### 3. 后端为什么用 FastAPI？

参考回答：

FastAPI 适合快速构建数据接口，支持类型标注和 Pydantic 模型，接口文档也能自动生成。这个项目需要给 React 前端提供多个结构化 JSON 接口，所以 FastAPI 很合适。

### 4. 前端为什么用 React？

参考回答：

React 适合组件化构建数据分析页面。项目中 KPI 卡片、表格、布局、图表都可以拆成组件复用。TypeScript 也能帮助约束接口返回类型，减少字段使用错误。

### 5. 数据流是怎样的？

参考回答：

数据先由 `nba_client.py` 从 demo 文件、缓存或 NBA API 读取，service 层使用 pandas 做筛选和转换，analytics 层做具体指标计算，schemas 层定义返回结构，FastAPI 返回 JSON。前端通过 `client.ts` 请求接口，再用页面组件展示成卡片、表格和图表。

### 6. 指标是怎么计算的？

参考回答：

基础指标和很多高级指标如 `OFF_RATING`、`DEF_RATING`、`TS_PCT` 主要来自 NBA API。项目自己计算的包括投篮区域的 `FGA`、`FGM`、`FG_PCT`、`PPS`，球员雷达图 0-100 分，比赛最大领先、领先变化、得分高潮等。

### 7. 雷达图的分数怎么来的？

参考回答：

雷达图先把基础数据和高级数据按球员 ID 合并，然后对每个指标做 min-max 归一化，转换成 0-100 分。每个维度由多个指标组成，比如得分维度包括 `PTS`、`TS_PCT`、`USG_PCT`，最后取这些指标分数的平均值。防守效率越低越好，所以做了反向归一化。

### 8. AI 问数是否真的可靠？

参考回答：

当前实现不是让 AI 凭空回答，而是先识别问题意图，再调用后端结构化数据接口，然后把数据上下文传给模型生成回答，所以比普通聊天更可靠。但它仍依赖模型分类和实体识别，如果问题模糊或数据不足，回答也会受影响。后续可以通过本地实体词典、工具调用和结果校验进一步提升可靠性。

### 9. Shot Chart 是怎么画出来的？

参考回答：

后端通过 NBA API 获取每次出手的 `LOC_X`、`LOC_Y` 坐标，前端 `ShotChart.tsx` 把这些坐标映射到 SVG 半场图上。命中用圆点表示，未命中用叉号表示，并通过 hover 显示投篮区域和动作类型。

### 10. 投篮热区的高效区域怎么判断？

参考回答：

后端先按 `SHOT_ZONE_BASIC`、`SHOT_ZONE_AREA`、`SHOT_ZONE_RANGE` 聚合，计算出手数、命中数、命中率、总得分和每次出手得分 `PPS`。然后设置最低出手数门槛，如果 `PPS >= 1.20` 就标记为高效区域，`PPS >= 1.00` 是常规区域，否则是低效区域。

### 11. 为什么要做缓存？

参考回答：

NBA API 可能响应慢或者临时不可用，而且重复请求同一赛季数据没有必要。缓存可以减少请求次数，提高页面响应速度，也让课堂演示更稳定。

### 12. 为什么这样设计页面？

参考回答：

页面按分析对象分模块：总览负责快速认识整体，比赛页负责从赛程进入复盘，球员页关注个人能力，球队页关注团队攻防，投篮页关注空间分布，智能问数降低用户使用门槛。这样的结构符合用户从宏观到局部、从列表到详情的使用习惯。

### 13. 项目的创新点是什么？

参考回答：

创新点主要是把篮球数据的多个层面整合到一个平台：既有传统表格，也有比赛走势、球员雷达、球队攻防象限、投篮热区；同时加入智能问数，让用户可以用自然语言探索结构化数据。

### 14. 和普通数据展示有什么区别？

参考回答：

普通数据展示通常只是把接口字段列成表格。本项目加入了数据处理和分析逻辑，比如比赛关键节点识别、投篮高效区域识别、雷达图归一化评分和焦点比赛评分，所以更接近数据分析应用，而不是简单看板。

### 15. 后续如何扩展？

参考回答：

可以扩展更多数据源，比如 CBA 或 NCAA；增加预测模型，比如比赛胜负预测或球员表现预测；完善数据库存储；优化 AI 问数为工具调用式系统；增加用户收藏、报告导出和对比分析功能。

---

## 十四、学习复习重点总结

### 1. 答辩最应该讲清楚的主线

```text
数据从哪里来
  -> 后端如何读取和缓存
  -> pandas 如何处理
  -> 指标如何计算
  -> FastAPI 如何返回
  -> React 如何请求
  -> 图表如何展示
  -> AI 如何基于数据回答
```

### 2. 最值得重点展示的文件

后端：

- `backend/app/main.py`
- `backend/app/services/nba_client.py`
- `backend/app/services/game_service.py`
- `backend/app/services/player_service.py`
- `backend/app/services/team_service.py`
- `backend/app/services/shot_service.py`
- `backend/app/services/query_service.py`
- `backend/app/analytics/game_flow.py`
- `backend/app/analytics/normalization.py`
- `backend/app/analytics/shot_analysis.py`

前端：

- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/pages/Players.tsx`
- `frontend/src/pages/Teams.tsx`
- `frontend/src/pages/Shots.tsx`
- `frontend/src/pages/AskAI.tsx`
- `frontend/src/charts/GameFlowChart.tsx`
- `frontend/src/charts/RadarChart.tsx`
- `frontend/src/charts/ShotChart.tsx`
- `frontend/src/charts/HeatMap.tsx`

### 3. 最容易被问到的技术点

- FastAPI 路由如何注册；
- React Router 如何加载页面；
- `useApi()` 如何管理异步请求；
- pandas 如何聚合投篮区域；
- 雷达图分数如何归一化；
- 防守效率为什么越低越好；
- AI 问数是不是基于真实数据；
- 缓存和 demo 模式如何保证答辩稳定。

### 4. 一句话总结项目

Hoop Insight 是一个基于 FastAPI、pandas 和 React 的篮球数据分析平台，它把 NBA 数据获取、缓存、指标分析、可视化和大模型问数整合起来，让用户能够从比赛、球员、球队和投篮空间多个角度理解篮球数据。

