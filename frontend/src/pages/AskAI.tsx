import { useState, type FormEvent } from "react";
import { ApiError, askAI, type AskAiResponse } from "../api/client";
import MarkdownContent from "../components/MarkdownContent";
import { AI_COPY, DATA_TYPE_LABELS } from "../constants/zhLabels";

type AskHistoryItem = {
  id: number;
  question: string;
  response: AskAiResponse;
  unconfigured: boolean;
};

type AnalysisMetric = {
  label?: string;
  value?: string | number | null;
  description?: string;
};

type AnalysisTable = {
  title?: string;
  columns?: string[];
  rows?: Array<Record<string, unknown>>;
};

type AnalysisChart = {
  type?: string;
  title?: string;
  points?: Array<{ label?: string; value?: number | string | null }>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeDataLabel(value: string) {
  const normalized = value.trim().toLowerCase();
  return DATA_TYPE_LABELS[normalized] ?? DATA_TYPE_LABELS[normalized.replace(/_data$/, "")] ?? value;
}

function inferDataTypes(response: AskAiResponse) {
  const labels = new Set<string>();

  response.need_data?.forEach((item) => {
    labels.add(normalizeDataLabel(item));
  });

  if (response.intent) {
    labels.add(normalizeDataLabel(response.intent));
  }

  if (isRecord(response.data)) {
    Object.keys(response.data).forEach((key) => {
      labels.add(normalizeDataLabel(key));
    });
  }

  if (labels.size === 0 && response.data) {
    labels.add("结构化数据");
  }

  return Array.from(labels).filter(Boolean);
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

function getAnalysis(response: AskAiResponse): Record<string, unknown> | null {
  if (isRecord(response.analysis)) {
    return response.analysis;
  }
  if (isRecord(response.data) && typeof response.data.intent_label === "string") {
    return response.data;
  }
  return null;
}

function getAnalysisMetrics(analysis: Record<string, unknown> | null): AnalysisMetric[] {
  const metrics = analysis?.core_metrics;
  if (!Array.isArray(metrics)) {
    return [];
  }
  return metrics.filter(isRecord).map((item) => ({
    label: typeof item.label === "string" ? item.label : undefined,
    value: typeof item.value === "string" || typeof item.value === "number" ? item.value : null,
    description: typeof item.description === "string" ? item.description : undefined,
  }));
}

function getAnalysisTables(analysis: Record<string, unknown> | null): AnalysisTable[] {
  const tables = analysis?.evidence_tables;
  if (!Array.isArray(tables)) {
    return [];
  }
  return tables.filter(isRecord).map((item) => ({
    title: typeof item.title === "string" ? item.title : "数据依据",
    columns: asStringArray(item.columns),
    rows: Array.isArray(item.rows) ? item.rows.filter(isRecord) : [],
  }));
}

function getAnalysisCharts(analysis: Record<string, unknown> | null): AnalysisChart[] {
  const charts = analysis?.charts;
  if (!Array.isArray(charts)) {
    return [];
  }
  return charts.filter(isRecord).map((item) => ({
    type: typeof item.type === "string" ? item.type : "bar",
    title: typeof item.title === "string" ? item.title : undefined,
    points: Array.isArray(item.points)
      ? item.points.filter(isRecord).map((point) => ({
          label: typeof point.label === "string" ? point.label : String(point.label ?? ""),
          value: typeof point.value === "number" || typeof point.value === "string" ? point.value : null,
        }))
      : [],
  }));
}

function getDebugPayload(response: AskAiResponse) {
  if (!isRecord(response.debug) || Object.keys(response.debug).length === 0) {
    return null;
  }
  return response.debug;
}

function displayCell(value: unknown) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }
  if (value === null || value === undefined || value === "") {
    return "暂无";
  }
  if (isRecord(value)) {
    return JSON.stringify(value);
  }
  return String(value);
}

function isAIUnconfiguredText(value: unknown) {
  if (typeof value !== "string") {
    return false;
  }

  const text = value.toLowerCase();
  return text.includes("未配置") || text.includes("没有配置") || text.includes("not configured") || text.includes("missing api key") || text.includes("llm") || text.includes("api key");
}

function EvidenceTable({ table }: { table: AnalysisTable }) {
  const rows = table.rows ?? [];
  const columns = table.columns?.length ? table.columns : Object.keys(rows[0] ?? {});

  if (rows.length === 0 || columns.length === 0) {
    return <div className="state-card">暂无可展示的数据依据。</div>;
  }

  return (
    <div className="qa-evidence-table-wrap">
      <table className="qa-evidence-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {columns.map((column) => (
                <td key={`${rowIndex}-${column}`}>{displayCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AnalysisChartCard({ chart }: { chart: AnalysisChart }) {
  const points = (chart.points ?? [])
    .map((point) => ({ label: point.label ?? "", value: typeof point.value === "number" ? point.value : Number(point.value) }))
    .filter((point) => Number.isFinite(point.value));

  if (points.length === 0) {
    return null;
  }

  const max = Math.max(...points.map((point) => point.value), 1);

  if (chart.type === "line") {
    const width = 520;
    const height = 160;
    const padding = 20;
    const yMin = Math.min(...points.map((point) => point.value), 0);
    const yMax = Math.max(...points.map((point) => point.value), 1);
    const range = yMax - yMin || 1;
    const polyline = points
      .map((point, index) => {
        const x = padding + (points.length === 1 ? 0 : (index / (points.length - 1)) * (width - padding * 2));
        const y = height - padding - ((point.value - yMin) / range) * (height - padding * 2);
        return `${x},${y}`;
      })
      .join(" ");

    return (
      <div className="qa-chart-card">
        <strong>{chart.title}</strong>
        <svg className="qa-line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={chart.title}>
          <polyline points={polyline} />
          {points.map((point, index) => {
            const x = padding + (points.length === 1 ? 0 : (index / (points.length - 1)) * (width - padding * 2));
            const y = height - padding - ((point.value - yMin) / range) * (height - padding * 2);
            return <circle key={`${point.label}-${index}`} cx={x} cy={y} r="4" />;
          })}
        </svg>
        <div className="qa-chart-labels">
          {points.map((point, index) => (
            <span key={`${point.label}-${index}`}>{point.label}</span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="qa-chart-card">
      <strong>{chart.title}</strong>
      <div className="qa-bar-list">
        {points.map((point, index) => (
          <div key={`${point.label}-${index}`} className="qa-bar-row">
            <span>{point.label}</span>
            <div className="qa-bar-track">
              <i style={{ width: `${Math.max(4, (point.value / max) * 100)}%` }} />
            </div>
            <em>{displayCell(point.value)}</em>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Component() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configHint, setConfigHint] = useState(false);
  const [answers, setAnswers] = useState<AskHistoryItem[]>([]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    setLoading(true);
    setError(null);
    setConfigHint(false);

    try {
      const response = await askAI(trimmedQuestion);
      const unconfigured = isAIUnconfiguredText(response.answer) || isAIUnconfiguredText(response.signal);
      setConfigHint(unconfigured);
      setAnswers((current) => [{ id: Date.now(), question: trimmedQuestion, response, unconfigured }, ...current]);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "AI 服务暂时不可用，请稍后再试。";
      setError(message);
      setConfigHint(caught instanceof ApiError ? caught.status === 502 || isAIUnconfiguredText(message) : isAIUnconfiguredText(message));
    } finally {
      setLoading(false);
    }
  }

  function applyExample(example: string) {
    setQuestion(example);
    setError(null);
  }

  return (
    <div className="page-stack">
      <section className="ai-panel">
        <div className="ask-ai-heading">
          <span>{AI_COPY.eyebrow}</span>
          <h2>{AI_COPY.title}</h2>
          <p>{AI_COPY.subtitle}</p>
        </div>

        <form className="prompt-box" onSubmit={handleSubmit}>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={AI_COPY.placeholder} rows={5} />
          <button type="submit" disabled={loading || question.trim().length === 0}>
            {loading ? "分析中……" : AI_COPY.submit}
          </button>
        </form>

        <div className="example-question-list" aria-label={AI_COPY.exampleAria}>
          {AI_COPY.examples.map((example) => (
            <button key={example} type="button" onClick={() => applyExample(example)}>
              {example}
            </button>
          ))}
        </div>

        {loading ? <div className="state-card ask-loading">{AI_COPY.loading}</div> : null}
        {configHint ? <div className="state-card ask-config-card">{AI_COPY.configHint}</div> : null}
        {error ? <div className="state-card state-card-error">请求失败：{error}</div> : null}
      </section>

      {answers.length > 0 ? (
        <section className="answer-stack">
          {answers.map((item) => {
            const answer = item.response.answer ?? item.response.signal ?? AI_COPY.answerFallback;
            const dataTypes = inferDataTypes(item.response);
            const analysis = getAnalysis(item.response);
            const intentLabel = typeof analysis?.intent_label === "string" ? analysis.intent_label : normalizeDataLabel(item.response.intent ?? "");
            const sourceTags = asStringArray(analysis?.used_tables).length ? asStringArray(analysis?.used_tables) : dataTypes;
            const metrics = getAnalysisMetrics(analysis);
            const tables = getAnalysisTables(analysis);
            const charts = getAnalysisCharts(analysis);
            const followUps = asStringArray(analysis?.follow_up_questions);
            const debugPayload = getDebugPayload(item.response);

            return (
              <article key={item.id} className="answer-card">
                <div className="answer-card-top">
                  <div>
                    <span>{AI_COPY.questionLabel}</span>
                    <h2>{item.question}</h2>
                  </div>
                  <small>{item.response.confidence ?? AI_COPY.confidenceFallback}</small>
                </div>

                <div className="qa-report-meta">
                  {intentLabel ? <span className="qa-intent-tag">{intentLabel}</span> : null}
                  {sourceTags.map((type) => (
                    <span key={type}>{normalizeDataLabel(type)}</span>
                  ))}
                </div>

                {dataTypes.length > 0 && !analysis ? (
                  <div className="data-type-list" aria-label={AI_COPY.dataTypeAria}>
                    {dataTypes.map((type) => (
                      <span key={type}>{type}</span>
                    ))}
                  </div>
                ) : null}

                {item.unconfigured ? <div className="state-card ask-config-card">{AI_COPY.unconfiguredAnswer}</div> : null}
                <MarkdownContent content={answer} />

                {metrics.length > 0 ? (
                  <div className="qa-metric-grid">
                    {metrics.slice(0, 5).map((metric) => (
                      <div className="qa-metric-card" key={`${metric.label}-${metric.value}`}>
                        <span>{metric.label}</span>
                        <strong>{metric.value}</strong>
                        {metric.description ? <p>{metric.description}</p> : null}
                      </div>
                    ))}
                  </div>
                ) : null}

                {charts.length > 0 ? (
                  <div className="qa-chart-grid">
                    {charts.slice(0, 2).map((chart, index) => (
                      <AnalysisChartCard key={`${chart.title}-${index}`} chart={chart} />
                    ))}
                  </div>
                ) : null}

                {tables.length > 0 ? (
                  <details className="qa-evidence-panel">
                    <summary>查看数据依据</summary>
                    <div className="qa-evidence-stack">
                      {tables.map((table, index) => (
                        <section key={`${table.title}-${index}`} className="qa-evidence-block">
                          <h3>{table.title}</h3>
                          <EvidenceTable table={table} />
                        </section>
                      ))}
                    </div>
                  </details>
                ) : null}

                {debugPayload ? (
                  <details className="qa-evidence-panel">
                    <summary>查看识别过程</summary>
                    <pre className="qa-debug-json">{JSON.stringify(debugPayload, null, 2)}</pre>
                  </details>
                ) : null}

                {followUps.length > 0 ? (
                  <div className="qa-followups" aria-label="推荐追问问题">
                    {followUps.map((followUp) => (
                      <button key={followUp} type="button" onClick={() => applyExample(followUp)}>
                        {followUp}
                      </button>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </section>
      ) : (
        <section className="empty-panel">
          <strong>{AI_COPY.emptyTitle}</strong>
          <span>{AI_COPY.emptyDescription}</span>
        </section>
      )}
    </div>
  );
}
