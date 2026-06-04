import { Link } from "react-router-dom";
import { getFocusGames, getRecentGames, getTodayGames, type GameSummary, type TeamGameSummary, useApi } from "../api/client";
import { formatDate, formatGameStatus, gameMatchup } from "../api/formatters";
import { AsyncStatus } from "../components/AsyncState";
import StatCard from "../components/StatCard";
import { COMMON_COPY } from "../constants/zhLabels";
import { translateTeamName } from "../utils/nameTranslations";

function teamName(team?: TeamGameSummary | null) {
  return translateTeamName(team?.abbreviation ?? team?.name ?? "暂无", "short");
}

function teamFullName(team?: TeamGameSummary | null) {
  const city = team?.city ? `${team.city} ` : "";
  return team?.name ? translateTeamName(`${city}${team.name}`, "full") : teamName(team);
}

function teamRecord(team?: TeamGameSummary | null) {
  if (typeof team?.wins === "number" && typeof team.losses === "number") {
    return `${team.wins}-${team.losses}`;
  }

  if (typeof team?.win_pct === "number") {
    return `${Math.round(team.win_pct * 1000) / 10}%`;
  }

  return "战绩暂无";
}

function scoreValue(team?: TeamGameSummary | null) {
  return typeof team?.score === "number" ? String(team.score) : "-";
}

function gameTime(game: Pick<GameSummary, "game_date" | "game_time_utc" | "status" | "status_text">) {
  if (game.status_text || game.status) {
    return formatGameStatus(game.status_text ?? game.status);
  }

  const value = game.game_time_utc ?? game.game_date;
  if (!value) {
    return "时间待定";
  }

  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function statusTone(status?: string | null) {
  const text = String(status ?? "").toLowerCase();
  if (text.includes("final")) {
    return "complete";
  }
  if (text.includes("progress") || text.includes("q") || text.includes(":")) {
    return "live";
  }
  return "scheduled";
}

function GameCard({ game }: { game: GameSummary }) {
  return (
    <article className="game-card">
      <div className="game-card-top">
        <span className={`status-pill status-pill-${statusTone(game.status_text ?? game.status)}`}>{formatGameStatus(game.status_text ?? game.status)}</span>
        <span>{formatDate(game.game_date ?? game.game_time_utc)}</span>
      </div>

      <div className="scoreboard-row">
        <div>
          <strong>{teamName(game.away_team)}</strong>
          <small>{teamFullName(game.away_team)}</small>
        </div>
        <b>{scoreValue(game.away_team)}</b>
      </div>
      <div className="scoreboard-row">
        <div>
          <strong>{teamName(game.home_team)}</strong>
          <small>{teamFullName(game.home_team)}</small>
        </div>
        <b>{scoreValue(game.home_team)}</b>
      </div>

      <div className="game-card-meta">
        <span>{teamRecord(game.away_team)}</span>
        <span>{teamRecord(game.home_team)}</span>
      </div>
      <Link className="text-link" to={`/games/${encodeURIComponent(game.game_id)}`}>
        查看比赛详情
      </Link>
    </article>
  );
}

function EmptyBlock({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-panel">
      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}

export function Component() {
  const recentGames = useApi(() => getRecentGames(), []);
  const todayGames = useApi(() => getTodayGames(), []);
  const focusGames = useApi(() => getFocusGames(), []);
  const today = todayGames.data?.games ?? [];
  const recent = recentGames.data?.games ?? [];
  const focus = focusGames.data?.games ?? [];
  const topFocus = focus[0];

  return (
    <div className="page-stack">
      <AsyncStatus loading={recentGames.loading || todayGames.loading || focusGames.loading} error={recentGames.error ?? todayGames.error ?? focusGames.error} />

      <section className="stat-grid">
        <StatCard label="今日比赛" value={String(today.length)} trend={formatDate(todayGames.data?.game_date)} tone="blue" />
        <StatCard label="近期比赛" value={String(recent.length)} trend="近 14 天" tone="violet" />
        <StatCard label="焦点对阵" value={String(focus.length)} trend="按信号排序" tone="green" />
        <StatCard label="可复盘比赛" value={String(recent.filter((game) => game.game_id).length)} trend="已关联比赛 ID" tone="amber" />
      </section>

      <section className="games-section">
        <div className="section-heading">
          <div>
            <h2>今日赛程</h2>
            <p>集中呈现比赛状态、比分和双方战绩，适合快速定位当日焦点。</p>
          </div>
          <span>{gameTime({ game_date: todayGames.data?.game_date })}</span>
        </div>
        {today.length > 0 ? (
          <div className="game-card-grid">
            {today.map((game) => (
              <GameCard game={game} key={game.game_id} />
            ))}
          </div>
        ) : (
          <EmptyBlock title="今日暂无比赛" description="当前没有可展示的当天赛程，请稍后刷新或切换演示数据。" />
        )}
      </section>

      <section className="focus-zone">
        <div className="focus-copy">
          <span>今日焦点对阵</span>
          <h2>{topFocus ? gameMatchup(topFocus) : "等待焦点信号"}</h2>
          <p>{topFocus ? "综合赛程可用性、胜率接近程度和近期状态信号生成推荐。" : "当今日或近期比赛数据可用时，这里会高亮最值得优先复盘的对阵。"}</p>
        </div>
        {topFocus ? (
          <div className="focus-summary">
            <div className="focus-score">
              <span>焦点分</span>
              <strong>{Math.round(topFocus.focus_score ?? 0)}</strong>
            </div>
            <div className="focus-reasons">
              {(topFocus.focus_reasons?.length ? topFocus.focus_reasons : ["焦点推荐原因将在信号可用后展示。"]).map((reason) => (
                <span key={reason}>{reason}</span>
              ))}
            </div>
            <Link className="primary-link" to={`/games/${encodeURIComponent(topFocus.game_id)}`}>
              打开复盘
            </Link>
          </div>
        ) : (
          <EmptyBlock title="暂无焦点对阵" description="焦点接口暂未返回可展示的比赛。" />
        )}
      </section>

      <section className="table-card">
        <div className="card-heading">
          <div>
            <h2>近期比赛明细</h2>
            <p>按比赛维度汇总对阵、日期、状态和比分，支持进入单场复盘。</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>对阵</th>
                <th>日期</th>
                <th>状态</th>
                <th>客队</th>
                <th>主队</th>
                <th>比分</th>
                <th>详情</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={7}>{COMMON_COPY.noData}</td>
                </tr>
              ) : (
                recent.map((game) => (
                  <tr key={game.game_id}>
                    <td>{gameMatchup(game)}</td>
                    <td>{formatDate(game.game_date ?? game.game_time_utc)}</td>
                    <td>{formatGameStatus(game.status_text ?? game.status)}</td>
                    <td>{teamName(game.away_team)}</td>
                    <td>{teamName(game.home_team)}</td>
                    <td>
                      {scoreValue(game.away_team)} - {scoreValue(game.home_team)}
                    </td>
                    <td>
                      <Link className="text-link" to={`/games/${encodeURIComponent(game.game_id)}`}>
                        复盘
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
