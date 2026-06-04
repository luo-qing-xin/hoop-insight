# 比赛接口示例

先在 `backend/` 目录启动后端服务：

```bash
uvicorn app.main:app --reload
```

## 近期已完成比赛

```bash
curl "http://127.0.0.1:8000/api/games/recent?season=2025-26&days=14"
```

## 今日赛程与实时比分

```bash
curl "http://127.0.0.1:8000/api/games/today"
```

## 焦点比赛推荐

接口会根据简单启发式信号对可复盘比赛排序。

```bash
curl "http://127.0.0.1:8000/api/games/focus"
```

## 单场比赛复盘

```bash
curl "http://127.0.0.1:8000/api/games/0022500001/review"
```
