import { useMemo, useState } from "react";
import {
  getDataCenterDataset,
  getDataCenterDatasets,
  useApi,
  type DataCenterDataset,
  type DataCenterDatasetSummary,
} from "../api/client";
import { AsyncStatus } from "../components/AsyncState";
import StatCard from "../components/StatCard";

type SortConfig = {
  column: string;
  direction: "asc" | "desc";
} | null;

type ChartPoint = {
  label: string;
  value: number;
};

type ChartBlock = {
  title: string;
  subtitle: string;
  data: ChartPoint[];
  lowerIsBetter?: boolean;
};

const DEFAULT_DATASETS: DataCenterDatasetSummary[] = [
  { key: "player_stats", label: "球员基础数据", folder: "processed", name: "player_stats", exists: false },
  { key: "team_stats", label: "球队基础数据", folder: "processed", name: "team_stats", exists: false },
  { key: "recent_games", label: "近期比赛数据", folder: "processed", name: "recent_games", exists: false },
  { key: "shot_chart", label: "投篮数据", folder: "processed", name: "shot_chart", exists: false },
  { key: "ai_question_history", label: "AI 问数历史数据", folder: "processed", name: "ai_question_history", exists: false },
];

const TEAM_COLUMNS = ["team", "team_name", "team_abbr", "TEAM_NAME", "TEAM_ABBREVIATION", "TEAM_ABBR"];
const PLAYER_COLUMNS = ["player", "player_name", "PLAYER_NAME"];
const DATE_COLUMNS = ["date", "game_date", "GAME_DATE", "asked_at"];

function valueToString(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function valueToNumber(value: unknown) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  const parsed = Number(String(value ?? "").replace(/,/g, ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function findColumn(columns: string[], aliases: string[]) {
  const normalized = new Map(columns.map((column) => [column.toLowerCase(), column]));
  for (const alias of aliases) {
    const matched = normalized.get(alias.toLowerCase());
    if (matched) {
      return matched;
    }
  }
  return null;
}

function uniqueValues(records: Array<Record<string, unknown>>, column: string | null) {
  if (!column) {
    return [];
  }
  return Array.from(new Set(records.map((row) => valueToString(row[column])).filter(Boolean))).sort((a, b) =>
    a.localeCompare(b, "zh-CN"),
  );
}

function formatFileSize(bytes: number) {
  if (!bytes) {
    return "0 KB";
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "暂无";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

function compareValues(a: unknown, b: unknown) {
  const leftNumber = valueToNumber(a);
  const rightNumber = valueToNumber(b);
  if (leftNumber !== null && rightNumber !== null) {
    return leftNumber - rightNumber;
  }
  return valueToString(a).localeCompare(valueToString(b), "zh-CN", { numeric: true });
}

function escapeCsvCell(value: unknown) {
  const text = valueToString(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function downloadCsv(label: string, columns: string[], records: Array<Record<string, unknown>>) {
  const csv = [columns.join(","), ...records.map((row) => columns.map((column) => escapeCsvCell(row[column])).join(","))].join("\n");
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${label || "dataset"}_filtered.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function topMetricBlock(
  title: string,
  subtitle: string,
  records: Array<Record<string, unknown>>,
  columns: string[],
  metricAliases: string[],
  labelAliases: string[],
  lowerIsBetter = false,
): ChartBlock | null {
  const metricColumn = findColumn(columns, metricAliases);
  const labelColumn = findColumn(columns, labelAliases);
  if (!metricColumn || !labelColumn) {
    return null;
  }

  const data = records
    .map((row) => ({ label: valueToString(row[labelColumn]), value: valueToNumber(row[metricColumn]) }))
    .filter((item): item is ChartPoint => Boolean(item.label) && item.value !== null)
    .sort((a, b) => (lowerIsBetter ? a.value - b.value : b.value - a.value))
    .slice(0, 10);

  return data.length ? { title, subtitle, data, lowerIsBetter } : null;
}

function buildPlayerCharts(dataset: DataCenterDataset): ChartBlock[] {
  return [
    topMetricBlock("得分 Top 10", "按得分字段自动识别生成", dataset.records, dataset.columns, ["pts", "PTS", "points"], PLAYER_COLUMNS),
    topMetricBlock("篮板 Top 10", "按篮板字段自动识别生成", dataset.records, dataset.columns, ["reb", "REB", "rebounds"], PLAYER_COLUMNS),
    topMetricBlock("助攻 Top 10", "按助攻字段自动识别生成", dataset.records, dataset.columns, ["ast", "AST", "assists"], PLAYER_COLUMNS),
  ].filter((block): block is ChartBlock => block !== null);
}

function buildTeamCharts(dataset: DataCenterDataset): ChartBlock[] {
  return [
    topMetricBlock(
      "进攻效率 Top 10",
      "OFF_RATING / offensive_rating",
      dataset.records,
      dataset.columns,
      ["OFF_RATING", "off_rating", "offensive_rating"],
      TEAM_COLUMNS,
    ),
    topMetricBlock(
      "防守效率 Top 10",
      "数值越低通常越好",
      dataset.records,
      dataset.columns,
      ["DEF_RATING", "def_rating", "defensive_rating"],
      TEAM_COLUMNS,
      true,
    ),
    topMetricBlock(
      "净效率 Top 10",
      "NET_RATING / net_rating",
      dataset.records,
      dataset.columns,
      ["NET_RATING", "net_rating"],
      TEAM_COLUMNS,
    ),
  ].filter((block): block is ChartBlock => block !== null);
}

function buildGameTrend(dataset: DataCenterDataset): ChartBlock | null {
  const dateColumn = findColumn(dataset.columns, DATE_COLUMNS);
  if (!dateColumn) {
    return null;
  }

  const counts = new Map<string, number>();
  dataset.records.forEach((row) => {
    const raw = valueToString(row[dateColumn]);
    if (!raw) {
      return;
    }
    const key = raw.slice(0, 10);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });

  const data = Array.from(counts.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([label, value]) => ({ label, value }));

  return data.length ? { title: "比赛日期趋势", subtitle: "按日期统计已保存比赛记录数", data } : null;
}

function buildAutoCharts(dataset: DataCenterDataset): ChartBlock[] {
  if (dataset.key.includes("player")) {
    return buildPlayerCharts(dataset);
  }
  if (dataset.key.includes("team")) {
    return buildTeamCharts(dataset);
  }
  if (dataset.key.includes("recent_games")) {
    return [buildGameTrend(dataset)].filter((block): block is ChartBlock => block !== null);
  }
  return [];
}

function MiniBarChart({ block }: { block: ChartBlock }) {
  const max = Math.max(...block.data.map((item) => Math.abs(item.value)), 1);

  return (
    <section className="data-viz-card">
      <div className="card-heading">
        <div>
          <h2>{block.title}</h2>
          <p>{block.subtitle}</p>
        </div>
      </div>
      <div className="data-center-bars">
        {block.data.map((item) => (
          <div className="data-center-bar-row" key={`${item.label}-${item.value}`}>
            <span>{item.label}</span>
            <div className="data-center-bar-track">
              <i
                className={item.value < 0 ? "negative" : undefined}
                style={{ width: `${Math.max((Math.abs(item.value) / max) * 100, 5)}%` }}
              />
            </div>
            <strong>{Number.isInteger(item.value) ? item.value : item.value.toFixed(2)}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function ScoreComparison({ dataset }: { dataset: DataCenterDataset }) {
  const homeScore = findColumn(dataset.columns, ["home_score"]);
  const awayScore = findColumn(dataset.columns, ["away_score"]);
  if (!homeScore || !awayScore || !dataset.key.includes("recent_games")) {
    return null;
  }

  const homeTeam = findColumn(dataset.columns, ["home_team", "home_team_name"]);
  const awayTeam = findColumn(dataset.columns, ["away_team", "away_team_name"]);
  const gameId = findColumn(dataset.columns, ["game_id", "GAME_ID"]);
  const rows = dataset.records.slice(0, 12);

  return (
    <section className="data-viz-card">
      <div className="card-heading">
        <div>
          <h2>主客队比分对比</h2>
          <p>展示最近保存的比赛比分记录</p>
        </div>
      </div>
      <div className="score-compare-list">
        {rows.map((row, index) => (
          <div className="score-compare-row" key={`${valueToString(row[gameId ?? ""])}-${index}`}>
            <span>{valueToString(row[awayTeam ?? ""]) || "客队"}</span>
            <strong>{valueToString(row[awayScore])}</strong>
            <em>:</em>
            <strong>{valueToString(row[homeScore])}</strong>
            <span>{valueToString(row[homeTeam ?? ""]) || "主队"}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Component() {
  const [datasetKey, setDatasetKey] = useState("player_stats");
  const [keyword, setKeyword] = useState("");
  const [team, setTeam] = useState("");
  const [player, setPlayer] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [sortConfig, setSortConfig] = useState<SortConfig>(null);

  const datasetListState = useApi(getDataCenterDatasets, []);
  const datasets = datasetListState.data?.datasets.length ? datasetListState.data.datasets : DEFAULT_DATASETS;
  const datasetState = useApi(() => getDataCenterDataset(datasetKey), [datasetKey]);
  const dataset = datasetState.data;

  const teamColumn = dataset ? findColumn(dataset.columns, TEAM_COLUMNS) : null;
  const playerColumn = dataset ? findColumn(dataset.columns, PLAYER_COLUMNS) : null;
  const dateColumn = dataset ? findColumn(dataset.columns, DATE_COLUMNS) : null;

  const teams = useMemo(() => uniqueValues(dataset?.records ?? [], teamColumn), [dataset, teamColumn]);
  const players = useMemo(() => uniqueValues(dataset?.records ?? [], playerColumn), [dataset, playerColumn]);

  const filteredRecords = useMemo(() => {
    const records = dataset?.records ?? [];
    const normalizedKeyword = keyword.trim().toLowerCase();
    const start = dateStart ? new Date(dateStart) : null;
    const end = dateEnd ? new Date(dateEnd) : null;

    const filtered = records.filter((row) => {
      if (normalizedKeyword) {
        const haystack = Object.values(row).map(valueToString).join(" ").toLowerCase();
        if (!haystack.includes(normalizedKeyword)) {
          return false;
        }
      }
      if (team && teamColumn && valueToString(row[teamColumn]) !== team) {
        return false;
      }
      if (player && playerColumn && valueToString(row[playerColumn]) !== player) {
        return false;
      }
      if ((start || end) && dateColumn) {
        const dateValue = new Date(valueToString(row[dateColumn]));
        if (Number.isNaN(dateValue.getTime())) {
          return false;
        }
        if (start && dateValue < start) {
          return false;
        }
        if (end) {
          const inclusiveEnd = new Date(end);
          inclusiveEnd.setHours(23, 59, 59, 999);
          if (dateValue > inclusiveEnd) {
            return false;
          }
        }
      }
      return true;
    });

    if (!sortConfig) {
      return filtered;
    }

    return [...filtered].sort((left, right) => {
      const result = compareValues(left[sortConfig.column], right[sortConfig.column]);
      return sortConfig.direction === "asc" ? result : -result;
    });
  }, [dataset, keyword, team, teamColumn, player, playerColumn, dateColumn, dateStart, dateEnd, sortConfig]);

  const visibleRecords = filteredRecords.slice(0, 500);
  const chartBlocks = dataset ? buildAutoCharts(dataset) : [];

  function updateSort(column: string) {
    setSortConfig((current) => {
      if (!current || current.column !== column) {
        return { column, direction: "asc" };
      }
      if (current.direction === "asc") {
        return { column, direction: "desc" };
      }
      return null;
    });
  }

  return (
    <div className="page-stack data-center-page">
      <section className="data-center-intro">
        <div>
          <span>Local Data Hub</span>
          <h2>数据中心</h2>
          <p>这里用于查看、筛选、下载项目中已经持久化保存的数据。</p>
        </div>
        <label>
          <span>数据集</span>
          <select
            value={datasetKey}
            onChange={(event) => {
              setDatasetKey(event.target.value);
              setKeyword("");
              setTeam("");
              setPlayer("");
              setDateStart("");
              setDateEnd("");
              setSortConfig(null);
            }}
          >
            {datasets.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
                {item.exists ? "" : "（未保存）"}
              </option>
            ))}
          </select>
        </label>
      </section>

      <AsyncStatus loading={datasetState.loading} error={datasetState.error ?? datasetListState.error} />

      {dataset && !dataset.metadata.exists ? (
        <section className="state-card">当前数据还没有保存，请先运行数据获取模块。</section>
      ) : null}

      {dataset && dataset.metadata.exists ? (
        <>
          <div className="stat-grid data-center-stat-grid">
            <StatCard label="总行数" value={dataset.metadata.rows.toLocaleString()} trend={`${filteredRecords.length} 条匹配`} />
            <StatCard label="总列数" value={dataset.metadata.columns.toLocaleString()} trend="字段数" />
            <StatCard label="缺失值" value={dataset.metadata.missing_values.toLocaleString()} trend="NA / 空值" tone="amber" />
            <StatCard label="文件大小" value={formatFileSize(dataset.metadata.file_size)} trend={formatDateTime(dataset.metadata.updated_at)} tone="green" />
          </div>

          <section className="data-center-controls">
            <label>
              <span>关键词搜索</span>
              <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索任意字段" />
            </label>
            {teamColumn ? (
              <label>
                <span>球队筛选</span>
                <select value={team} onChange={(event) => setTeam(event.target.value)}>
                  <option value="">全部球队</option>
                  {teams.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {playerColumn ? (
              <label>
                <span>球员筛选</span>
                <select value={player} onChange={(event) => setPlayer(event.target.value)}>
                  <option value="">全部球员</option>
                  {players.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {dateColumn ? (
              <>
                <label>
                  <span>开始日期</span>
                  <input type="date" value={dateStart} onChange={(event) => setDateStart(event.target.value)} />
                </label>
                <label>
                  <span>结束日期</span>
                  <input type="date" value={dateEnd} onChange={(event) => setDateEnd(event.target.value)} />
                </label>
              </>
            ) : null}
            <button className="primary-button" type="button" onClick={() => downloadCsv(dataset.label, dataset.columns, filteredRecords)}>
              下载当前数据
            </button>
          </section>

          <section className="data-center-viz-grid">
            {chartBlocks.length ? chartBlocks.map((block) => <MiniBarChart key={block.title} block={block} />) : <section className="state-card">当前数据字段暂不支持自动图表生成</section>}
            <ScoreComparison dataset={dataset} />
          </section>

          <section className="table-card data-center-table-card">
            <div className="card-heading">
              <div>
                <h2>{dataset.label}</h2>
                <p>
                  共 {dataset.metadata.rows.toLocaleString()} 行，当前筛选 {filteredRecords.length.toLocaleString()} 行。
                  {filteredRecords.length > 500 ? " 表格仅展示前 500 行。" : ""}
                </p>
              </div>
              <span>最近更新时间：{formatDateTime(dataset.metadata.updated_at)}</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {dataset.columns.map((column) => (
                      <th key={column}>
                        <button className="sort-header-button" type="button" onClick={() => updateSort(column)}>
                          {column}
                          {sortConfig?.column === column ? (sortConfig.direction === "asc" ? " ↑" : " ↓") : ""}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visibleRecords.length ? (
                    visibleRecords.map((row, rowIndex) => (
                      <tr key={`${rowIndex}-${dataset.key}`}>
                        {dataset.columns.map((column) => (
                          <td key={column}>{valueToString(row[column]) || "暂无"}</td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={dataset.columns.length || 1}>暂无匹配数据</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
