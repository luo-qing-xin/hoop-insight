# Hoop Insight Mac 本地运行指南

这份文档面向第一次在 Mac 上运行本项目的同学，按步骤操作即可启动本地开发环境。

## 1. 项目简介

Hoop Insight 是一个篮球数据分析与智能问数系统。项目采用前后端分离结构：

- 后端：`backend/app/main.py`，使用 FastAPI 提供比赛、球队、球员、投篮、数据中心和 AI 问数接口。
- 前端：`frontend/`，使用 React + TypeScript + Vite 构建数据分析工作台。
- 数据：`data/raw/` 和 `data/processed/` 中保存 NBA 原始数据和处理后的演示数据。
- AI：后端通过 OpenAI Chat Completions 兼容接口调用大模型，可用于自然语言问数和分析报告生成。

本项目不是 Streamlit 项目，根目录未发现 `app.py`、`main.py` 或 `streamlit_app.py` 作为页面入口；真实启动方式是分别启动 FastAPI 后端和 Vite 前端。

## 2. Mac 运行前准备

建议先安装或确认以下工具：

- Git：用于克隆项目。
- Python 3：用于运行 FastAPI 后端。
- pip：用于安装 Python 依赖。
- venv：Python 自带虚拟环境工具。
- Node.js 和 npm：用于运行 React/Vite 前端。
- VS Code：可选，用于查看和编辑代码。
- Homebrew：可选，用于安装 Git、Python、Node.js 等工具。

检查命令：

```bash
git --version
python3 --version
pip3 --version
node --version
npm --version
```

如果没有安装 Homebrew，可到官网查看安装方式：

```text
https://brew.sh/
```

安装 Node.js 的一种方式：

```bash
brew install node
```

## 3. 克隆项目到本地

```bash
git clone https://github.com/luo-qing-xin/hoop-insight.git
cd hoop-insight
```

如果 GitHub 提示没有权限：

- 先确认仓库是否为公开仓库；
- 如果是私有仓库，确认当前 GitHub 账号是否有访问权限；
- 如果使用 SSH 克隆，确认本机 SSH Key 已添加到 GitHub。

## 4. 创建并激活后端虚拟环境

本项目的 Python 依赖文件在 `backend/requirements.txt`，建议把虚拟环境创建在 `backend/.venv`：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

激活成功后，终端命令行前面通常会出现 `(.venv)`。

如果后续要退出虚拟环境：

```bash
deactivate
```

## 5. 安装依赖

### 5.1 安装后端依赖

确认当前目录是 `backend/`，并且已经激活虚拟环境：

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

本项目当前未发现 `pyproject.toml` 或 `environment.yml`，因此不需要执行 `pip install -e .` 或 Conda 环境安装命令。

后端依赖包括 FastAPI、Uvicorn、Pandas、Requests、python-dotenv、nba_api、SQLAlchemy 等。如果安装失败，优先检查：

- Python 版本是否可用；
- 虚拟环境是否已激活；
- pip 是否已升级；
- 网络是否能访问 PyPI；
- M 系列 Mac 上某些包如果需要编译，可能还需要安装 Xcode Command Line Tools：

```bash
xcode-select --install
```

### 5.2 安装前端依赖

新开一个终端，或先回到项目根目录：

```bash
cd ../frontend
npm install
```

前端依赖和脚本定义在 `frontend/package.json`，启动脚本是 `npm run dev`。

## 6. 配置环境变量

后端会从环境变量或 `backend/.env` 读取配置。项目已经提供示例文件：

```bash
cd ../backend
cp .env.example .env
```

`.env` 文件必须放在 `backend/` 目录下，不是项目根目录。

当前代码中使用的环境变量如下：

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

说明：

- `DEMO_MODE=true` 时，后端会优先读取 `data/processed/` 中的本地演示数据。
- `DEMO_MODE=false` 时，后端会尝试通过 `nba_api` 获取实时或在线 NBA 数据，并把数据缓存到本地。
- `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 用于配置 OpenAI 兼容的大模型服务，例如小米 MiMo、OpenAI、SiliconFlow 或其他兼容 Chat Completions 的服务。
- 不要把真实 API Key 写进文档或提交到 GitHub。
- `.gitignore` 已忽略 `.env` 和 `.env.*`，但保留 `.env.example`。

如果暂时没有大模型 API Key，也可以先运行项目；AI 问数相关功能会提示“AI 功能未配置”，其他数据页面仍可使用。

前端默认请求后端地址 `http://127.0.0.1:8000`。如果需要修改，可在 `frontend/.env.local` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 7. 准备数据

项目中已经存在数据目录：

- `data/raw/`：NBA API 原始数据缓存或导出的原始 CSV。
- `data/processed/`：前端展示和演示模式常用的处理后数据。

当前 `data/processed/` 已包含多份可用演示数据，例如：

- `games.csv`
- `league_game_log.csv`
- `players_base.csv`
- `players_advanced.csv`
- `teams_base.csv`
- `teams_advanced.csv`
- `teams_four_factors.csv`
- `teams_defense.csv`
- `teams_opponent.csv`
- `shots.csv`
- `shot_chart.csv`
- `play_by_play.csv`
- `box_scores.csv`

如果你希望优先使用这些本地数据，请在 `backend/.env` 中设置：

```env
DEMO_MODE=true
DEMO_DATA_DIR=../data/processed
```

修改 `.env` 后需要重启后端。

如果 `data/processed/` 为空，但 `data/cache/nba/` 中已有 NBA API 缓存，可以运行导出演示数据脚本：

```bash
cd ..
python scripts/export_demo_data.py
```

注意：该脚本会读取 `backend/.env` 中的 `NBA_CACHE_DIR` 和 `DEMO_DATA_DIR`。如果缓存目录不存在，脚本会提示 `Cache directory does not exist`。

如果没有本地演示数据，也没有缓存数据，且 `DEMO_MODE=false`，后端会尝试通过 `nba_api` 联网获取数据。网络不稳定或 NBA 接口不可用时，页面可能出现空表、加载失败或接口错误。

## 8. 启动项目

本项目需要分别启动后端和前端。

### 8.1 启动后端

打开第一个终端：

```bash
cd hoop-insight/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

默认后端地址：

```text
http://127.0.0.1:8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

如果返回下面内容，说明后端启动成功：

```json
{"status":"ok"}
```

### 8.2 启动前端

打开第二个终端：

```bash
cd hoop-insight/frontend
npm run dev
```

默认前端地址通常是：

```text
http://127.0.0.1:5173
```

浏览器通常不会总是自动打开。如果没有自动打开，请复制终端显示的本地地址到浏览器访问。

## 9. 常见问题与解决方法

### 问题 1：`python: command not found`

Mac 上通常使用 `python3`：

```bash
python3 --version
```

创建虚拟环境也使用：

```bash
python3 -m venv .venv
```

### 问题 2：`pip: command not found`

可以使用：

```bash
python3 -m pip install --upgrade pip
```

如果已经激活虚拟环境，也可以使用：

```bash
pip install --upgrade pip
```

### 问题 3：依赖安装失败

建议按顺序检查：

- 是否已经进入 `backend/` 并激活 `.venv`；
- `python3 --version` 是否正常；
- `pip install --upgrade pip` 是否执行成功；
- 网络是否能访问 PyPI；
- M 系列 Mac 如果出现编译错误，尝试安装 Xcode Command Line Tools：

```bash
xcode-select --install
```

### 问题 4：后端端口被占用

FastAPI 默认使用 `8000` 端口。如果端口被占用，可以改用 `8001`：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

同时需要让前端请求新端口，在 `frontend/.env.local` 中写入：

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

然后重启前端。

### 问题 5：前端端口被占用

Vite 默认使用 `5173` 端口。如果端口被占用，可以改用 `5174`：

```bash
cd frontend
npm run dev -- --port 5174
```

### 问题 6：API Key 报错或 AI 功能不可用

检查以下内容：

- `backend/.env` 是否存在；
- `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 变量名是否和示例一致；
- API Key 是否有效；
- `LLM_BASE_URL` 是否为 OpenAI Chat Completions 兼容服务地址；
- 是否已安装 `python-dotenv`；
- 当前网络是否能访问对应 API 服务。

如果没有配置大模型，项目仍可启动，但 AI 问数和报告生成会返回“AI 功能未配置”。

### 问题 7：页面打开但没有数据

检查以下内容：

- `backend/.env` 中是否设置了 `DEMO_MODE=true`；
- `DEMO_DATA_DIR=../data/processed` 是否正确；
- `data/processed/` 中是否存在对应 CSV 文件；
- 后端终端是否有读取数据或 NBA API 请求错误；
- 如果使用在线数据，确认网络能访问 NBA API；
- 修改 `.env` 后是否已经重启后端。

### 问题 8：`uvicorn: command not found`

通常是后端依赖没有安装，或虚拟环境没有激活：

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 问题 9：`npm: command not found`

说明 Node.js/npm 未安装或未加入 PATH。可以通过 Homebrew 安装：

```bash
brew install node
node --version
npm --version
```

## 10. 一键运行建议

项目已提供 Mac 本地快捷启动脚本：

```bash
chmod +x scripts/run_mac.sh
./scripts/run_mac.sh
```

该脚本会：

- 检查 `backend/.venv` 是否存在；
- 检查 `frontend/node_modules` 是否存在；
- 启动后端 `uvicorn app.main:app --reload`；
- 启动前端 `npm run dev`；
- 当前端进程退出时，自动停止后台后端进程。

首次运行前仍然需要先手动完成：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

然后安装前端依赖：

```bash
cd ../frontend
npm install
```

如果想临时修改端口，可以这样运行：

```bash
BACKEND_PORT=8001 FRONTEND_PORT=5174 ./scripts/run_mac.sh
```

同时记得在 `frontend/.env.local` 中配置对应后端地址：

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

## 11. 推荐运行顺序汇总

完整首次运行流程：

```bash
git clone https://github.com/luo-qing-xin/hoop-insight.git
cd hoop-insight

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

如需使用本地演示数据，编辑 `backend/.env`：

```env
DEMO_MODE=true
DEMO_DATA_DIR=../data/processed
```

安装前端依赖：

```bash
cd ../frontend
npm install
```

方式一：分别启动两个终端。

终端 1：

```bash
cd hoop-insight/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

终端 2：

```bash
cd hoop-insight/frontend
npm run dev
```

方式二：使用快捷脚本。

```bash
cd hoop-insight
chmod +x scripts/run_mac.sh
./scripts/run_mac.sh
```

访问前端：

```text
http://127.0.0.1:5173
```

