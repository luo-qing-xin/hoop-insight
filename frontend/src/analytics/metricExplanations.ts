export type MetricExplanation = {
  name: string;
  meaning: string;
  direction: string;
  interpretation: string;
};

export const METRIC_EXPLANATIONS: Record<string, MetricExplanation> = {
  PTS: {
    name: "得分",
    meaning: "球员或球队在比赛中得到的总分。",
    direction: "越高越好",
    interpretation: "直接反映终结和产量，但需要结合出手数、命中率和比赛节奏判断效率。",
  },
  REB: {
    name: "篮板",
    meaning: "抢到的进攻篮板和防守篮板总数。",
    direction: "通常越高越好",
    interpretation: "体现争抢球权和终结防守回合的能力，内线球员和快节奏球队通常更高。",
  },
  AST: {
    name: "助攻",
    meaning: "传球直接帮助队友完成得分的次数。",
    direction: "通常越高越好",
    interpretation: "反映组织和带动队友的能力，需要结合失误和球权占用一起看。",
  },
  STL: {
    name: "抢断",
    meaning: "通过防守夺回球权的次数。",
    direction: "越高越好",
    interpretation: "代表防守侵略性和预判能力，但过度赌博式防守可能带来失位风险。",
  },
  BLK: {
    name: "盖帽",
    meaning: "成功封盖对手投篮的次数。",
    direction: "越高越好",
    interpretation: "体现护框和干扰投篮能力，也要结合犯规和对手篮下命中率判断防守质量。",
  },
  TOV: {
    name: "失误",
    meaning: "因传球、控球或进攻犯规等原因丢失球权的次数。",
    direction: "越低越好",
    interpretation: "失误越少，进攻回合损耗越低；高持球核心需要结合助攻和使用率评估。",
  },
  FG_PCT: {
    name: "投篮命中率",
    meaning: "投篮命中数占投篮出手数的比例。",
    direction: "越高越好",
    interpretation: "衡量整体投篮准度，但没有区分两分和三分的价值差异。",
  },
  FG3_PCT: {
    name: "三分命中率",
    meaning: "三分命中数占三分出手数的比例。",
    direction: "越高越好",
    interpretation: "体现外线投射效率，需要结合三分出手量判断稳定性和威胁程度。",
  },
  FT_PCT: {
    name: "罚球命中率",
    meaning: "罚球命中数占罚球出手数的比例。",
    direction: "越高越好",
    interpretation: "反映罚球稳定性，关键时刻和高造罚球员尤其重要。",
  },
  OFF_RATING: {
    name: "进攻效率",
    meaning: "每 100 回合得到的分数。",
    direction: "越高越好",
    interpretation: "比场均得分更能剔除节奏影响，适合比较球队或球员进攻产出。",
  },
  DEF_RATING: {
    name: "防守效率",
    meaning: "每 100 回合失掉的分数。",
    direction: "越低越好",
    interpretation: "数值越低代表每 100 回合让对手得分越少，是核心防守效率指标。",
  },
  NET_RATING: {
    name: "净效率",
    meaning: "进攻效率减去防守效率后的每 100 回合净胜分。",
    direction: "越高越好",
    interpretation: "综合衡量攻防强弱，正值代表每 100 回合净胜对手，越高通常竞争力越强。",
  },
  TS_PCT: {
    name: "真实命中率",
    meaning: "同时考虑两分、三分和罚球价值的综合得分效率。",
    direction: "越高越好",
    interpretation: "比普通命中率更接近真实得分效率，适合比较不同出手结构的球员。",
  },
  EFG_PCT: {
    name: "有效命中率",
    meaning: "把三分球额外价值计入后的投篮命中率。",
    direction: "越高越好",
    interpretation: "适合衡量投篮效率，但不包含罚球贡献。",
  },
  USG_PCT: {
    name: "使用率",
    meaning: "球员在场时由其终结的球队进攻回合比例。",
    direction: "不固定，取决于角色",
    interpretation: "高使用率说明承担更多进攻责任，需要结合效率判断是高效核心还是低效消耗球权。",
  },
  AST_PCT: {
    name: "助攻率",
    meaning: "球员在场时助攻队友命中的比例估算。",
    direction: "通常越高越好",
    interpretation: "体现组织参与度，高控卫通常更高；需要结合失误率判断传控质量。",
  },
  REB_PCT: {
    name: "篮板率",
    meaning: "球员或球队抢到可争抢篮板的比例。",
    direction: "越高越好",
    interpretation: "比篮板总数更能剔除出场时间和节奏影响，适合跨角色比较篮板能力。",
  },
  PACE: {
    name: "比赛节奏",
    meaning: "每 48 分钟估算回合数。",
    direction: "不固定，取决于战术",
    interpretation: "数值越高代表攻防转换越快；快慢本身不是优劣，要结合攻防效率判断效果。",
  },
  PIE: {
    name: "比赛影响力指数",
    meaning: "综合得分、篮板、助攻、防守数据和负面数据后的贡献占比。",
    direction: "越高越好",
    interpretation: "用于快速观察综合影响力，但仍应结合角色、出场时间和具体技术特点解读。",
  },
};

const LOCALIZED_KEYS: Record<string, string> = {
  得分: "PTS",
  篮板: "REB",
  助攻: "AST",
  抢断: "STL",
  盖帽: "BLK",
  失误: "TOV",
  投篮命中率: "FG_PCT",
  三分命中率: "FG3_PCT",
  罚球命中率: "FT_PCT",
  进攻效率: "OFF_RATING",
  防守效率: "DEF_RATING",
  净效率: "NET_RATING",
  真实命中率: "TS_PCT",
  有效命中率: "EFG_PCT",
  使用率: "USG_PCT",
  助攻率: "AST_PCT",
  篮板率: "REB_PCT",
  节奏: "PACE",
  比赛节奏: "PACE",
  比赛影响力指数: "PIE",
};

function normalizeMetricKey(label: string) {
  return label.trim().replace(/\s+/g, "_").replace(/-/g, "_").toUpperCase();
}

export function getMetricExplanation(label: string): MetricExplanation | undefined {
  return METRIC_EXPLANATIONS[LOCALIZED_KEYS[label.trim()] ?? normalizeMetricKey(label)];
}
