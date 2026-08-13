export const APP_COPY = {
  brand: "Hoop Insight",
  brandSubtitle: "篮球智能分析平台",
  eyebrow: "Hoop Insight",
  liveModelLabel: "实时数据源",
  liveApiTitle: "FastAPI 实时接入",
  liveApiDescription: "后端可用时，页面会直接读取最新接口数据；离线演示时可切换本地 Demo 数据。",
  liveApiStatus: "连接正常",
};

export type PageCopy = {
  title: string;
  eyebrow?: string;
  description: string;
};

export const PAGE_COPY: Record<string, PageCopy> = {
  "/": {
    title: "数据总览",
    eyebrow: "DATA OVERVIEW",
    description:
      "Hoop Insight 将比赛结果、球队效率、球员表现与投篮空间数据整合到统一分析视图中，帮助快速识别联盟趋势、球队差异与关键表现波动。",
  },
  "/games": {
    title: "近期比赛",
    eyebrow: "RECENT GAMES",
    description: "聚合近期赛程、比分状态与焦点对阵，快速进入单场复盘。",
  },
  "/players": {
    title: "球员分析",
    eyebrow: "PLAYER ANALYSIS",
    description: "从基础数据、高级指标与能力结构理解球员表现。",
  },
  "/teams": {
    title: "球队分析",
    eyebrow: "TEAM ANALYSIS",
    description: "从进攻效率、防守效率、比赛节奏和净效率理解球队竞争力。",
  },
  "/shots": {
    title: "投篮分析",
    eyebrow: "SHOOTING ANALYSIS",
    description: "结合出手位置、区域效率和命中转化识别投篮结构。",
  },
  "/data-center": {
    title: "数据中心",
    eyebrow: "DATA CENTER",
    description: "查看、筛选、下载已保存到本地的数据集，供榜单、球队分析、投篮热区和 AI 问数复用。",
  },
  "/ask-ai": {
    title: "智能问数",
    eyebrow: "AI Q&A",
    description: "用自然语言探索比赛、球员与球队表现。",
  },
};

export const GAME_DETAIL_COPY: PageCopy = {
  title: "比赛复盘",
  description: "拆解比分走势、关键节点、球队对比和高影响力球员表现。",
};

export const NAV_ITEMS = [
  { to: "/", label: "数据总览", mark: "总" },
  { to: "/games", label: "近期比赛", mark: "赛" },
  { to: "/players", label: "球员分析", mark: "员" },
  { to: "/teams", label: "球队分析", mark: "队" },
  { to: "/shots", label: "投篮分析", mark: "投" },
  { to: "/ask-ai", label: "智能问数", mark: "AI" },
  { to: "/data-center", label: "数据中心", mark: "数" },
];

export const COMMON_COPY = {
  noData: "暂无可用数据，请调整筛选条件后重试。",
  none: "暂无",
  loading: "正在加载实时篮球数据...",
  loadFailed: "数据加载失败",
  requestFailed: "请求失败，请稍后重试。",
  rankUnavailable: "排名暂无",
  liveData: "实时数据",
  lastSevenGames: "近 7 场",
  season: "赛季",
  team: "球队",
  player: "球员",
  players: "名球员",
  games: "场比赛",
  zones: "个区域",
};

export const AI_COPY = {
  title: "智能问数",
  eyebrow: "自然语言分析",
  subtitle: "用自然语言探索比赛、球员与球队表现。",
  placeholder: "请输入你想分析的问题，例如：湖人最近五场进攻效率如何？",
  submit: "生成分析",
  loading: "正在分析数据并生成回答...",
  emptyTitle: "开始一次数据提问",
  emptyDescription: "输入一个问题，系统会结合当前数据生成分析结论。",
  configHint: "AI 服务尚未配置。请在后端环境变量中补充 LLM API Key、Base URL 和模型名称后再使用智能问数。",
  unconfiguredAnswer: "AI 服务尚未配置，当前仅返回配置提示，暂未生成分析结论。",
  answerFallback: "暂无回答。",
  confidenceFallback: "模型分析",
  questionLabel: "问题",
  dataTypeAria: "本次回答使用的数据类型",
  exampleAria: "示例问题",
  examples: [
    "最近三场比赛是哪些",
    "最近三场比赛中，哪位球员得分表现最稳定？",
    "哪支球队的进攻效率最高？",
    "库里的投篮热区有什么特点？",
    "请生成一份今日焦点比赛分析报告。",
  ],
};

export const DATA_TYPE_LABELS: Record<string, string> = {
  game: "比赛数据",
  games: "比赛数据",
  game_query: "比赛数据",
  focus_game_report: "焦点比赛报告",
  daily_focus_report: "焦点比赛报告",
  game_recap_report: "比赛复盘",
  recent_games: "近期比赛",
  league_game_log: "比赛日志",
  recent_games_query: "最近比赛列表",
  recent_games_summary: "近期比赛总结",
  player: "球员数据",
  players: "球员数据",
  player_query: "球员数据",
  team: "球队数据",
  teams: "球队数据",
  team_query: "球队数据",
  shot: "投篮数据",
  shots: "投篮数据",
  shot_query: "投篮数据",
  comparison_query: "对比数据",
};

export const METRIC_LABELS: Record<string, string> = {
  PTS: "得分",
  POINTS: "得分",
  REB: "篮板",
  REBOUNDS: "篮板",
  AST: "助攻",
  ASSISTS: "助攻",
  STL: "抢断",
  STEALS: "抢断",
  BLK: "盖帽",
  BLOCKS: "盖帽",
  TOV: "失误",
  TURNOVERS: "失误",
  PF: "犯规",
  FG_PCT: "投篮命中率",
  "FG%": "投篮命中率",
  FG3_PCT: "三分命中率",
  "3P%": "三分命中率",
  FT_PCT: "罚球命中率",
  "FT%": "罚球命中率",
  OFF_RATING: "进攻效率",
  ORTG: "进攻效率",
  DEF_RATING: "防守效率",
  DRTG: "防守效率",
  NET_RATING: "净效率",
  USG_PCT: "使用率",
  TS_PCT: "真实命中率",
  EFG_PCT: "有效命中率",
  AST_PCT: "助攻率",
  REB_PCT: "篮板率",
  PACE: "比赛节奏",
  PIE: "比赛影响力指数",
  MIN: "出场时间",
  GP: "场次",
  FGA: "出手次数",
  FGM: "命中次数",
  PPS: "每次出手得分",
};

export const KPI_LABELS: Record<string, string> = {
  "League Offensive Rating": "联盟进攻效率",
  "League Defensive Rating": "联盟防守效率",
  "League Net Rating": "联盟净效率",
  "League Pace": "联盟比赛节奏",
};

export const KPI_TRENDS: Record<string, string> = {
  "Average points per 100 possessions": "每 100 回合平均得分，衡量整体进攻产出。",
  "Average points allowed per 100 possessions": "每 100 回合平均失分，数值越低代表防守越好。",
  "Average scoring margin per 100 possessions": "进攻效率与防守效率之差，反映整体胜负强度。",
  "Average possessions per 48 minutes": "每场平均回合数，用于衡量比赛速度。",
};

export const STATUS_LABELS: Record<string, string> = {
  final: "已结束",
  scheduled: "未开始",
  live: "进行中",
  progress: "进行中",
};

export const SHOT_ZONE_LABELS: Record<string, string> = {
  Backcourt: "后场",
  "Above the Break 3": "弧顶三分",
  "Left Corner 3": "左侧底角三分",
  "Right Corner 3": "右侧底角三分",
  "Corner 3": "底角三分",
  "Mid-Range": "中距离",
  "In The Paint": "禁区",
  "Restricted Area": "合理冲撞区",
  "Less Than 8 ft.": "8 英尺以内",
  "8-16 ft.": "8-16 英尺",
  "16-24 ft.": "16-24 英尺",
  "24+ ft.": "24 英尺以上",
  Center: "中路",
  "Left Side": "左侧",
  "Right Side": "右侧",
  "Left Side Center": "左侧 45 度",
  "Right Side Center": "右侧 45 度",
};

export const EFFICIENCY_LEVEL_LABELS: Record<string, string> = {
  high: "高效区域",
  normal: "常规区域",
  low: "低效区域",
};

export const MOMENT_LABELS: Record<string, string> = {
  max_lead: "最大领先",
  lead_change: "领先变化",
  scoring_run: "得分高潮",
  clutch_score: "关键得分",
};

export const RADAR_LABELS: Record<string, string> = {
  scoring: "得分",
  shooting: "投射",
  playmaking: "组织",
  rebounding: "篮板",
  defense: "防守",
  efficiency: "效率",
  impact: "影响力",
};

export function normalizeKey(label: string) {
  return label.trim().replace(/\s+/g, "_").replace(/-/g, "_").toUpperCase();
}

export function metricLabel(label: string) {
  return METRIC_LABELS[label] ?? METRIC_LABELS[normalizeKey(label)] ?? label;
}

export function shotZoneLabel(value?: string | null) {
  if (!value) {
    return "未知区域";
  }

  return SHOT_ZONE_LABELS[value] ?? value;
}

export function efficiencyLevelLabel(value?: string | null) {
  const key = String(value ?? "normal").toLowerCase();
  return EFFICIENCY_LEVEL_LABELS[key] ?? EFFICIENCY_LEVEL_LABELS.normal;
}

export function statusLabel(value?: string | null) {
  const text = String(value ?? "").trim();
  const normalized = text.toLowerCase();
  if (!normalized) {
    return "未开始";
  }
  if (normalized.includes("final") || normalized.includes("ended") || normalized.includes("complete")) {
    return STATUS_LABELS.final;
  }
  if (normalized.includes("scheduled")) {
    return STATUS_LABELS.scheduled;
  }
  if (normalized.includes("progress") || normalized.includes("live") || normalized.includes("q") || normalized.includes(":")) {
    return STATUS_LABELS.live;
  }
  return text;
}

export function radarLabel(label: string) {
  const key = label.trim().toLowerCase().replace(/\s+/g, "_");
  return RADAR_LABELS[key] ?? metricLabel(label);
}
