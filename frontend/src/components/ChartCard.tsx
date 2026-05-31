import { COMMON_COPY } from "../constants/zhLabels";

type ChartPoint = {
  label: string;
  value: number;
};

type ChartCardProps = {
  title: string;
  subtitle: string;
  data: ChartPoint[];
  variant?: "bars" | "line";
  metaLabel?: string;
  insight?: string;
};

function SparkleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3 9.8 9.8 3 12l6.8 2.2L12 21l2.2-6.8L21 12l-6.8-2.2L12 3Z" />
      <path d="M5 3v4" />
      <path d="M3 5h4" />
      <path d="M19 17v4" />
      <path d="M17 19h4" />
    </svg>
  );
}

export default function ChartCard({ title, subtitle, data, variant = "bars", metaLabel = COMMON_COPY.lastSevenGames, insight }: ChartCardProps) {
  const values = data.map((item) => item.value);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  const points = data
    .map((item, index) => {
      const x = data.length === 1 ? 50 : 6 + (index / (data.length - 1)) * 88;
      const y = 84 - ((item.value - min) / range) * 62;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <section className="chart-card">
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span>{metaLabel}</span>
      </div>

      {variant === "line" ? (
        <div className="line-chart" aria-label={title}>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none">
            <polyline points={points} />
            {data.map((item, index) => {
              const x = data.length === 1 ? 50 : 6 + (index / (data.length - 1)) * 88;
              const y = 84 - ((item.value - min) / range) * 62;

              return <circle key={item.label} cx={x} cy={y} r="1.35" />;
            })}
          </svg>
          <div className="chart-labels">
            {data.map((item) => (
              <span key={item.label}>{item.label}</span>
            ))}
          </div>
        </div>
      ) : (
        <div className="bar-chart" aria-label={title}>
          {data.map((item) => (
            <div className="bar-item" key={item.label}>
              <div className="bar-track">
                <span style={{ height: `${Math.max((item.value / max) * 100, 12)}%` }} />
              </div>
              <small>{item.label}</small>
            </div>
          ))}
        </div>
      )}

      {insight ? (
        <div className="insight-strip">
          <span className="insight-icon">
            <SparkleIcon />
          </span>
          <p>{insight}</p>
        </div>
      ) : null}
    </section>
  );
}
