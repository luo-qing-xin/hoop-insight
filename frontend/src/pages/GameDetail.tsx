import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { generateGameAiReport, getGameReview, type GameAiReportResponse, type GameReviewResponse, useApi } from "../api/client";
import { formatNumber, formatPercent } from "../api/formatters";
import GameFlowChart from "../charts/GameFlowChart";
import { AsyncStatus } from "../components/AsyncState";
import MarkdownContent from "../components/MarkdownContent";
import StatCard from "../components/StatCard";
import { COMMON_COPY, MOMENT_LABELS } from "../constants/zhLabels";
import { translatePlayerName, translateTeamName } from "../utils/nameTranslations";

type LooseRecord = Record<string, unknown>;

function asRecord(value: unknown): LooseRecord | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as LooseRecord) : null;
}

function readNumber(record: LooseRecord | null | undefined, keys: string[]) {
  if (!record) {
    return null;
  }

  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) {
      return Number(value);
    }
  }

  return null;
}

function readString(record: LooseRecord | null | undefined, keys: string[], fallback = "暂无") {
  if (!record) {
    return fallback;
  }

  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return fallback;
}

function scoreText(score: unknown) {
  const finalScore = asRecord(score);
  const home = readNumber(finalScore, ["home"]);
  const away = readNumber(finalScore, ["away"]);
  return home === null || away === null ? "暂无" : `${away} - ${home}`;
}

function winnerText(value: unknown) {
  if (value === "home") {
    return "主队";
  }
  if (value === "away") {
    return "客队";
  }
  if (value === "tie") {
    return "平局";
  }
  return COMMON_COPY.none;
}

function periodRows(flow: GameReviewResponse["game_flow"]) {
  const lastByPeriod = new Map<number, GameReviewResponse["game_flow"][number]>();

  flow.forEach((point) => {
    if (typeof point.period === "number") {
      lastByPeriod.set(point.period, point);
    }
  });

  let previousHome = 0;
  let previousAway = 0;

  return Array.from(lastByPeriod.entries())
    .sort(([periodA], [periodB]) => periodA - periodB)
    .map(([period, point]) => {
      const home = point.home_score - previousHome;
      const away = point.away_score - previousAway;
      previousHome = point.home_score;
      previousAway = point.away_score;

      return {
        period,
        away,
        home,
        total: `${point.away_score} - ${point.home_score}`,
      };
    });
}

function momentLabel(type: unknown) {
  const labels: Record<string, string> = {
    ...MOMENT_LABELS,
  };

  return typeof type === "string" ? labels[type] ?? type : "比赛节点";
}

function displayMoment(moment: LooseRecord) {
  const description = readString(moment, ["description"], "");
  if (description) {
    return description;
  }

  const margin = readNumber(moment, ["score_margin"]);
  const points = readNumber(moment, ["points", "lead"]);
  if (points !== null) {
    return `${momentLabel(moment.type)}，${points} 分`;
  }
  if (margin !== null) {
    return `${momentLabel(moment.type)}，分差 ${margin > 0 ? "+" : ""}${margin}`;
  }
  return momentLabel(moment.type);
}

function teamComparison(review?: GameReviewResponse | null) {
  const comparison = asRecord(review?.team_comparison);
  const home = asRecord(comparison?.home);
  const away = asRecord(comparison?.away);
  return { home, away };
}

const comparisonMetrics = [
  { label: "得分", keys: ["pts", "points"], format: "number" },
  { label: "篮板", keys: ["reb", "rebounds"], format: "number" },
  { label: "助攻", keys: ["ast", "assists"], format: "number" },
  { label: "抢断", keys: ["stl", "steals"], format: "number" },
  { label: "盖帽", keys: ["blk", "blocks"], format: "number" },
  { label: "失误", keys: ["tov", "to", "turnovers"], format: "number" },
  { label: "投篮命中率", keys: ["fg_pct"], format: "percent" },
  { label: "三分命中率", keys: ["fg3_pct"], format: "percent" },
];

function formatMetric(value: number | null, format: string) {
  if (value === null) {
    return COMMON_COPY.none;
  }

  return format === "percent" ? formatPercent(value) : formatNumber(value, 0);
}

export function Component() {
  const { gameId } = useParams();
  const review = useApi(() => (gameId ? getGameReview(gameId) : Promise.reject(new Error("缺少比赛 ID"))), [gameId]);
  const [aiReport, setAiReport] = useState<GameAiReportResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const currentGameIdRef = useRef(gameId);
  const data = review.data;
  const summary: LooseRecord = data?.basic_summary ?? {};
  const finalScore = asRecord(summary.final_score);
  const { home, away } = teamComparison(data);
  const homeLabel = translateTeamName(readString(home, ["abbreviation", "name"], "主队"), "short");
  const awayLabel = translateTeamName(readString(away, ["abbreviation", "name"], "客队"), "short");
  const periods = periodRows(data?.game_flow ?? []);
  const moments = (data?.key_moments ?? []).map(asRecord).filter((moment): moment is LooseRecord => Boolean(moment));
  const chartEvents = moments.map((moment) => ({
    period: readNumber(moment, ["period"]),
    game_clock: readString(moment, ["game_clock"], ""),
    description: readString(moment, ["description"], ""),
    type: readString(moment, ["type"], ""),
  }));
  const playerRows = (data?.top_players ?? []).map(asRecord).filter((player): player is LooseRecord => Boolean(player));

  useEffect(() => {
    currentGameIdRef.current = gameId;
    setAiReport(null);
    setAiError(null);
    setAiLoading(false);
  }, [gameId]);

  async function handleGenerateReport(forceRefresh = false) {
    if (!gameId || aiLoading) {
      return;
    }

    const requestedGameId = gameId;
    setAiLoading(true);
    setAiError(null);

    try {
      const response = await generateGameAiReport(requestedGameId, forceRefresh);
      if (currentGameIdRef.current !== requestedGameId) {
        return;
      }
      if (!response.success) {
        console.error("AI report generation failed", {
          gameId: requestedGameId,
          error: response.error,
          message: response.message,
          response,
        });
        setAiError(response.message || "AI 报告生成失败，请稍后重试。");
        return;
      }
      if (!response.report_markdown) {
        console.error("AI report response missing report_markdown", {
          gameId: requestedGameId,
          response,
        });
        setAiError(response.message || "大模型返回内容为空，请稍后重试。");
        return;
      }
      setAiReport(response);
    } catch (caught) {
      if (currentGameIdRef.current !== requestedGameId) {
        return;
      }
      console.error("AI report request failed", {
        gameId: requestedGameId,
        error: caught,
      });
      setAiError(caught instanceof Error ? caught.message : "AI 报告生成失败，请稍后重试。");
    } finally {
      if (currentGameIdRef.current === requestedGameId) {
        setAiLoading(false);
      }
    }
  }

  return (
    <div className="page-stack">
      <AsyncStatus loading={review.loading} error={review.error} empty={Boolean(data && !data.ok)} emptyMessage={data?.message ?? "暂无比赛复盘数据，请确认比赛 ID 或切换演示数据。"} />

      <section className="detail-banner game-detail-banner">
        <div>
          <span>比赛基础信息</span>
          <strong>{scoreText(summary.final_score)}</strong>
          <p>比赛 ID：{gameId ?? "暂无"}</p>
        </div>
        <div className="detail-score-meta">
          <span>{awayLabel}</span>
          <b>{readNumber(finalScore, ["away"]) ?? "-"}</b>
          <span>{homeLabel}</span>
          <b>{readNumber(finalScore, ["home"]) ?? "-"}</b>
        </div>
      </section>

      <section className="stat-grid">
        <StatCard label="胜方" value={winnerText(summary.winner)} trend="终场结果" tone="blue" />
        <StatCard label="主队最大领先" value={String(readNumber(summary, ["max_home_lead"]) ?? "暂无")} trend={homeLabel} tone="violet" />
        <StatCard label="客队最大领先" value={String(readNumber(summary, ["max_away_lead"]) ?? "暂无")} trend={awayLabel} tone="green" />
        <StatCard label="领先变化 / 平分" value={`${readNumber(summary, ["lead_changes"]) ?? 0} / ${readNumber(summary, ["tie_count"]) ?? 0}`} trend="走势" tone="amber" />
      </section>

      <section className="table-card">
        <div className="card-heading">
          <div>
            <h2>分节得分走势</h2>
            <p>根据逐回合累计比分推导每节得分，辅助判断比赛转折。</p>
          </div>
        </div>
        <div className="period-score-grid">
          {periods.length === 0 ? (
            <div className="empty-panel">{COMMON_COPY.noData}</div>
          ) : (
            periods.map((period) => (
              <div className="period-score" key={period.period}>
                <span>{period.period <= 4 ? `第 ${period.period} 节` : `加时 ${period.period - 4}`}</span>
                <strong>
                  {period.away} - {period.home}
                </strong>
                <small>总分 {period.total}</small>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="comparison-card">
        <div className="card-heading">
          <div>
            <h2>球队表现对比</h2>
            <p>
              {awayLabel} vs {homeLabel}
            </p>
          </div>
        </div>
        {home || away ? (
          <div className="comparison-list">
            {comparisonMetrics.map((metric) => {
              const awayValue = readNumber(away, metric.keys);
              const homeValue = readNumber(home, metric.keys);
              const max = Math.max(awayValue ?? 0, homeValue ?? 0, 1);

              return (
                <div className="comparison-row" key={metric.label}>
                  <span>{formatMetric(awayValue, metric.format)}</span>
                  <div>
                    <small>{metric.label}</small>
                    <div className="comparison-bars">
                      <i style={{ width: `${Math.max(((awayValue ?? 0) / max) * 100, awayValue === null ? 0 : 8)}%` }} />
                      <b style={{ width: `${Math.max(((homeValue ?? 0) / max) * 100, homeValue === null ? 0 : 8)}%` }} />
                    </div>
                  </div>
                  <span>{formatMetric(homeValue, metric.format)}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-panel">暂无球队技术统计对比，请等待后端返回箱线数据。</div>
        )}
      </section>

      <GameFlowChart points={data?.game_flow ?? []} events={chartEvents} homeLabel={homeLabel} awayLabel={awayLabel} />

      <section className="detail-grid">
        <section className="table-card">
          <div className="card-heading">
            <div>
              <h2>关键节点</h2>
              <p>提炼最大领先、领先变化、得分高潮和关键时刻得分。</p>
            </div>
          </div>
          {moments.length === 0 ? (
            <div className="empty-panel">暂未检测到关键节点。</div>
          ) : (
            <ol className="moment-list">
              {moments.slice(0, 8).map((moment, index) => (
                <li key={`${readString(moment, ["type"], "moment")}-${index}`}>
                  <span>{readString(moment, ["game_clock"], "暂无")}</span>
                  <div>
                    <strong>{momentLabel(moment.type)}</strong>
                    <p>{displayMoment(moment)}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="table-card">
          <div className="card-heading">
            <div>
              <h2>高影响力球员</h2>
              <p>按后端影响力分排序，快速识别左右比赛走势的球员。</p>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>球员</th>
                  <th>球队</th>
                  <th>得分</th>
                  <th>篮板</th>
                  <th>助攻</th>
                  <th>影响力</th>
                </tr>
              </thead>
              <tbody>
                {playerRows.length === 0 ? (
                  <tr>
                    <td colSpan={6}>{COMMON_COPY.noData}</td>
                  </tr>
                ) : (
                  playerRows.map((player) => (
                    <tr key={readString(player, ["player_name"])}>
                      <td>{translatePlayerName(readString(player, ["player_name"]), "full")}</td>
                      <td>{translateTeamName(readString(player, ["team_abbreviation"]), "short")}</td>
                      <td>{readNumber(player, ["points"]) ?? COMMON_COPY.none}</td>
                      <td>{readNumber(player, ["rebounds"]) ?? COMMON_COPY.none}</td>
                      <td>{readNumber(player, ["assists"]) ?? COMMON_COPY.none}</td>
                      <td>{formatNumber(readNumber(player, ["impact_score"]))}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>

      <section className="ai-report-card">
        <div className="card-heading ai-report-heading">
          <div>
            <span className="ai-report-tag">AI 复盘</span>
            <h2>AI 生成分析报告</h2>
            <p>基于当前比赛的比分走势、关键节点、球队对比和高影响力球员生成中文 Markdown 复盘。</p>
          </div>
          <div className="ai-report-actions">
            {aiReport?.generated_at ? (
              <small>
                {aiReport.cached ? "已缓存" : "最新生成"} · {new Date(aiReport.generated_at).toLocaleString("zh-CN")}
              </small>
            ) : null}
            <button type="button" onClick={() => handleGenerateReport(Boolean(aiReport))} disabled={aiLoading || review.loading || !gameId || Boolean(data && !data.ok)}>
              {aiLoading ? "生成中..." : aiReport ? "重新生成" : "生成 AI 报告"}
            </button>
          </div>
        </div>

        {aiLoading ? <div className="ai-report-status">正在生成比赛分析报告，请稍候...</div> : null}
        {aiError ? <div className="ai-report-error">{aiError}</div> : null}

        {aiReport?.success && aiReport.report_markdown ? (
          <>
            <MarkdownContent content={aiReport.report_markdown} className="markdown-answer ai-report-content" />
            <p className="ai-report-footnote">报告基于当前页面可用比赛数据生成，若实时数据不完整，分析可能受限。</p>
          </>
        ) : !aiLoading && !aiError ? (
          <div className="ai-report-empty">
            <strong>等待生成</strong>
            <span>点击按钮后，后端会按当前 game_id 聚合真实比赛数据并调用大模型生成报告。</span>
          </div>
        ) : null}
      </section>
    </div>
  );
}
