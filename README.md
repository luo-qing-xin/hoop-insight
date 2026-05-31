# Hoop Insight 篮球智能分析平台

Hoop Insight 是一个面向课程展示和后续迭代的篮球数据分析系统。项目通过 FastAPI 提供比赛、球队、球员、投篮区域和智能问数接口，前端使用 React + TypeScript 构建数据分析工作台，帮助用户从结构化数据中快速获得比赛洞察。

## 技术栈

- 后端：Python + FastAPI + pytest
- 前端：React + Vite + TypeScript
- 数据缓存：SQLite / 本地 JSON 缓存
- 智能问数：兼容 OpenAI Chat Completions 的 LLM 接口

## 项目结构

```text
backend/
  app/
    api/
    analytics/
    core/
    db/
    schemas/
    services/
  tests/
frontend/
  src/
    api/
    charts/
    components/
    constants/
    pages/
    styles/
data/
  raw/
  processed/
  cache/
scripts/
docs/
notebooks/
```

## 后端配置

后端配置从环境变量或 `backend/.env` 读取。首次运行可以复制示例配置：

```bash
cd backend
cp .env.example .env
```

Windows PowerShell：

```powershell
cd backend
Copy-Item .env.example .env
```

常用配置：

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

当 AI 配置为空时，后端不会中断服务；智能问数页面会提示用户补充 LLM API Key、Base URL 和模型名称。

## 运行后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

默认 API 地址为 `http://127.0.0.1:8000`。健康检查：

```bash
curl http://127.0.0.1:8000/health
```

运行后端测试：

```bash
cd backend
pytest
```

## 运行前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址为 `http://127.0.0.1:5173`。如需指定后端地址，可在前端环境变量中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

类型检查：

```bash
cd frontend
npm run typecheck
```

生产构建：

```bash
cd frontend
npm run build
```

## 开启演示数据模式

`DEMO_MODE=true` 时，后端会优先从 `DEMO_DATA_DIR` 读取本地演示数据，适合没有实时 NBA API 数据或网络不稳定时进行课程展示。

```env
DEMO_MODE=true
DEMO_DATA_DIR=../data/processed
```

修改 `backend/.env` 后重启后端：

```bash
cd backend
uvicorn app.main:app --reload
```

## 准备演示数据

如果已经有本地 NBA 缓存，可以导出为演示数据：

```bash
python scripts/export_demo_data.py
```

默认写入 `data/processed`。常见文件包括：

- `games.csv`
- `scoreboard.json`
- `players_base.csv`
- `players_advanced.csv`
- `teams_base.csv`
- `teams_advanced.csv`
- `shots.csv`
- `play_by_play.csv`
- `box_scores.csv`

准备好数据后，将 `backend/.env` 中的 `DEMO_MODE` 改为 `true`，然后重启后端即可让前端使用演示数据。
