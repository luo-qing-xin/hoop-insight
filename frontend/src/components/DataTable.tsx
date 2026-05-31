import { getMetricExplanation } from "../analytics/metricExplanations";
import { COMMON_COPY } from "../constants/zhLabels";

type DataTableProps = {
  columns: string[];
  rows: Array<Record<string, string | number>>;
  title?: string;
  subtitle?: string;
  actionLabel?: string;
};

function isCompleteStatus(column: string, value: string | number) {
  return column === "状态" && String(value).includes("已结束");
}

export default function DataTable({ columns, rows, title = "数据明细", subtitle = "来自后端接口的结构化数据。", actionLabel }: DataTableProps) {
  return (
    <section className="table-card">
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        {actionLabel ? (
          <a className="table-action" href="/games">
            {actionLabel}
          </a>
        ) : null}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((column) => {
                const explanation = getMetricExplanation(column);

                return (
                  <th key={column}>
                    <span className="column-heading">
                      {column}
                      {explanation ? (
                        <span
                          className="metric-tooltip"
                          tabIndex={0}
                          aria-label={`${explanation.name} 指标解释`}
                          title={`${explanation.name}: ${explanation.meaning} ${explanation.direction}。${explanation.interpretation}`}
                        >
                          ?
                          <span className="metric-tooltip-panel" role="tooltip">
                            <strong>{explanation.name}</strong>
                            <span>{explanation.meaning}</span>
                            <span>{explanation.direction}</span>
                            <span>{explanation.interpretation}</span>
                          </span>
                        </span>
                      ) : null}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length}>{COMMON_COPY.noData}</td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={`${rowIndex}-${Object.values(row).join("-")}`}>
                  {columns.map((column) => {
                    const value = row[column] ?? COMMON_COPY.none;

                    return (
                      <td key={column}>
                        {isCompleteStatus(column, value) ? <span className="status-chip status-chip-complete">{value}</span> : value}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
