import { useEffect, useMemo, useState } from "react";
import {
  getDataCenterDataset,
  getDataCenterDatasets,
  getDataCenterDownloadUrl,
  useApi,
  type DataCenterDataset,
  type DataCenterDatasetSummary,
} from "../api/client";
import { AsyncStatus } from "../components/AsyncState";
import StatCard from "../components/StatCard";

const DATA_TABS = [
  { key: "全部数据", label: "全部数据" },
  { key: "比赛数据", label: "比赛数据" },
  { key: "球员数据", label: "球员数据" },
  { key: "球队数据", label: "球队数据" },
  { key: "投篮数据", label: "投篮数据" },
  { key: "AI 问答日志", label: "AI 日志" },
  { key: "其他数据", label: "其他数据" },
];

const SOURCE_PAGE_SIZE = 8;
const PREVIEW_ROW_LIMIT = 10;

type DetailTab = "summary" | "schema" | "preview" | "download";

function valueToString(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function formatNumber(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString() : "暂无数据";
}

function formatFileSize(bytes?: number | null) {
  if (!bytes) {
    return "暂无数据";
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "暂无数据";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

function formatKpiDateTime(value?: string | null) {
  if (!value) {
    return { date: "暂无数据", time: "", full: "暂无数据" };
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return { date: value, time: "", full: value };
  }

  return {
    date: date.toLocaleDateString("zh-CN"),
    time: date.toLocaleTimeString("zh-CN", { hour12: false }),
    full: date.toLocaleString("zh-CN", { hour12: false }),
  };
}

function statusClass(status?: string) {
  if (status === "读取失败") {
    return "data-status data-status-error";
  }
  if (status === "空文件") {
    return "data-status data-status-muted";
  }
  return "data-status";
}

function isDatasetAvailable(dataset?: DataCenterDataset | null) {
  return Boolean(dataset && dataset.status !== "读取失败" && dataset.metadata.exists);
}

function MetaGrid({ dataset }: { dataset: DataCenterDataset }) {
  const items = [
    ["数据名称", dataset.label],
    ["数据来源", dataset.source],
    ["数据格式", dataset.data_format],
    ["数据路径", dataset.source_path],
    ["总行数", formatNumber(dataset.metadata.rows)],
    ["总列数", formatNumber(dataset.metadata.columns)],
    ["缺失值数量", formatNumber(dataset.metadata.missing_values)],
    ["重复行数量", formatNumber(dataset.metadata.duplicate_rows)],
    ["最近更新时间", formatDateTime(dataset.metadata.updated_at)],
  ];

  return (
    <div className="data-meta-grid">
      {items.map(([label, value]) => (
        <div className="data-meta-item" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function DatasetPicker({
  datasets,
  datasetKey,
  onPick,
}: {
  datasets: DataCenterDatasetSummary[];
  datasetKey: string;
  onPick: (key: string) => void;
}) {
  return (
    <label className="data-picker">
      <span>当前数据表</span>
      <select value={datasetKey} onChange={(event) => onPick(event.target.value)}>
        {datasets.map((item) => (
          <option key={item.key} value={item.key}>
            {item.label} · {item.data_type} · {item.data_format}
          </option>
        ))}
      </select>
    </label>
  );
}

function SourceTable({
  datasets,
  selectedKey,
  onPick,
}: {
  datasets: DataCenterDatasetSummary[];
  selectedKey: string;
  onPick: (key: string) => void;
}) {
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(datasets.length / SOURCE_PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageStart = (safePage - 1) * SOURCE_PAGE_SIZE;
  const visibleRows = datasets.slice(pageStart, pageStart + SOURCE_PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [datasets]);

  useEffect(() => {
    if (page > pageCount) {
      setPage(pageCount);
    }
  }, [page, pageCount]);

  return (
    <section className="table-card data-center-table-card data-source-panel">
      <div className="card-heading">
        <div>
          <h2>数据来源与格式</h2>
          <p>核心来源列表分页展示，完整路径、字段结构和原始预览在右侧详情中查看。</p>
        </div>
        <span>{datasets.length ? `${datasets.length} 个对象` : "暂无数据"}</span>
      </div>
      <div className="table-wrap">
        <table className="data-source-table">
          <thead>
            <tr>
              <th>数据名称</th>
              <th>数据类型</th>
              <th>数据格式</th>
              <th>文件大小</th>
              <th>行数</th>
              <th>列数</th>
              <th>当前状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.length ? (
              visibleRows.map((item) => (
                <tr
                  key={item.key}
                  className={item.key === selectedKey ? "selected-row" : undefined}
                  onClick={() => onPick(item.key)}
                >
                  <td>
                    <button className="link-button" type="button" onClick={() => onPick(item.key)}>
                      {item.label}
                    </button>
                  </td>
                  <td>{item.data_type}</td>
                  <td>{item.data_format}</td>
                  <td>{formatFileSize(item.file_size)}</td>
                  <td>{formatNumber(item.rows)}</td>
                  <td>{formatNumber(item.columns)}</td>
                  <td>
                    <span className={statusClass(item.status)}>{item.status || "无法识别"}</span>
                  </td>
                  <td>
                    <button
                      className="ghost-button compact-action"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onPick(item.key);
                      }}
                    >
                      查看详情
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8}>当前项目暂未检测到原始数据文件。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="table-pagination">
        <span>
          第 {safePage} / {pageCount} 页 · 每页 {SOURCE_PAGE_SIZE} 条
        </span>
        <div>
          <button type="button" disabled={safePage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
            上一页
          </button>
          <button type="button" disabled={safePage >= pageCount} onClick={() => setPage((current) => Math.min(pageCount, current + 1))}>
            下一页
          </button>
        </div>
      </div>
    </section>
  );
}

function DatasetDetailPanel({
  dataset,
  allDatasets,
  keyword,
  rows,
  matchedRows,
  onKeywordChange,
}: {
  dataset?: DataCenterDataset | null;
  allDatasets: DataCenterDatasetSummary[];
  keyword: string;
  rows: Array<Record<string, unknown>>;
  matchedRows: number;
  onKeywordChange: (value: string) => void;
}) {
  const [detailTab, setDetailTab] = useState<DetailTab>("summary");
  const downloadable = allDatasets.filter((item) => item.status !== "读取失败" && (item.rows ?? 0) > 0);

  useEffect(() => {
    setDetailTab("summary");
  }, [dataset?.key]);

  if (!dataset) {
    return (
      <section className="table-card data-center-detail-panel">
        <div className="empty-panel">请选择左侧数据对象查看字段结构、原始数据预览和下载入口。</div>
      </section>
    );
  }

  if (dataset.status === "读取失败") {
    return (
      <section className="table-card data-center-detail-panel">
        <div className="card-heading">
          <div>
            <h2>{dataset.label}</h2>
            <p>{dataset.source_path}</p>
          </div>
          <span className={statusClass(dataset.status)}>{dataset.status}</span>
        </div>
        <div className="state-card state-card-error">该数据文件读取失败：{dataset.error || "无法识别具体原因。"}</div>
      </section>
    );
  }

  const isAvailable = isDatasetAvailable(dataset);
  const visiblePreviewRows = rows.slice(0, PREVIEW_ROW_LIMIT);

  return (
    <section className="table-card data-center-detail-panel">
      <div className="data-detail-heading">
        <div>
          <span>Selected Dataset</span>
          <h2>{dataset.label}</h2>
          <p>{dataset.source_path}</p>
        </div>
        {isAvailable ? (
          <a className="ghost-button compact-action" href={getDataCenterDownloadUrl(dataset.key)}>
            下载 CSV
          </a>
        ) : (
          <span className={statusClass(dataset.status)}>{dataset.status || "暂无数据"}</span>
        )}
      </div>

      <div className="data-detail-tabs" aria-label="数据详情">
        {[
          { key: "summary", label: "摘要" },
          { key: "schema", label: "字段结构" },
          { key: "preview", label: "原始预览" },
          { key: "download", label: "下载" },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={detailTab === tab.key ? "active" : undefined}
            onClick={() => setDetailTab(tab.key as DetailTab)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="data-detail-body">
        {detailTab === "summary" ? (
          <>
            <MetaGrid dataset={dataset} />
            <div className="data-detail-summary">
              <div>
                <span>读取状态</span>
                <strong>{dataset.status || "无法识别"}</strong>
              </div>
              <div>
                <span>编码方式</span>
                <strong>{dataset.encoding || "无法识别"}</strong>
              </div>
              <div>
                <span>字段数量</span>
                <strong>{formatNumber(dataset.schema.length)}</strong>
              </div>
              <div>
                <span>页面预览</span>
                <strong>{dataset.is_truncated ? `${dataset.api_record_limit.toLocaleString()} 行内搜索` : "完整载入"}</strong>
              </div>
            </div>
          </>
        ) : null}

        {detailTab === "schema" ? (
          <div className="table-wrap data-detail-table-wrap">
            <table className="schema-table">
              <thead>
                <tr>
                  <th>字段名</th>
                  <th>数据类型 dtype</th>
                  <th>非空数量</th>
                  <th>缺失值数量</th>
                  <th>缺失率</th>
                  <th>示例值</th>
                  <th>中文解释</th>
                </tr>
              </thead>
              <tbody>
                {dataset.schema.length ? (
                  dataset.schema.map((field) => (
                    <tr key={field.field_name}>
                      <td>{field.field_name}</td>
                      <td>{field.dtype}</td>
                      <td>{formatNumber(field.non_null_count)}</td>
                      <td>{formatNumber(field.missing_count)}</td>
                      <td>{field.missing_rate.toFixed(2)}%</td>
                      <td>{field.sample_value || "暂无"}</td>
                      <td>{field.zh_explanation}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7}>当前数据表暂无字段结构。</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : null}

        {detailTab === "preview" ? (
          <div className="data-preview-panel">
            <div className="data-preview-toolbar">
              <label>
                <span>关键词搜索</span>
                <input value={keyword} onChange={(event) => onKeywordChange(event.target.value)} placeholder="搜索字段名或数据内容" />
              </label>
              <div className="match-count">
                <span>匹配行数</span>
                <strong>{matchedRows.toLocaleString()}</strong>
              </div>
            </div>
            <div className="table-wrap data-detail-table-wrap">
              <table className="raw-preview-table">
                <thead>
                  <tr>
                    {dataset.columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataset.metadata.rows === 0 ? (
                    <tr>
                      <td colSpan={dataset.columns.length || 1}>该数据文件为空，暂无可预览内容。</td>
                    </tr>
                  ) : visiblePreviewRows.length ? (
                    visiblePreviewRows.map((row, rowIndex) => (
                      <tr key={`${dataset.key}-${rowIndex}`}>
                        {dataset.columns.map((column) => (
                          <td key={column}>{valueToString(row[column]) || "暂无"}</td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={dataset.columns.length || 1}>{keyword ? "未找到匹配数据。" : "暂无可预览内容。"}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="data-preview-note">
              预览显示前 {PREVIEW_ROW_LIMIT} 条匹配记录。
              {dataset.is_truncated ? ` 当前接口最多载入 ${dataset.api_record_limit.toLocaleString()} 行用于页面搜索。` : ""}
            </p>
          </div>
        ) : null}

        {detailTab === "download" ? (
          <div className="download-grid data-detail-download-grid">
            {downloadable.length ? (
              downloadable.map((item) => (
                <div className="download-item" key={item.key}>
                  <div>
                    <strong>{item.label}</strong>
                    <span>
                      {item.data_type} · {item.data_format} · {formatNumber(item.rows)} 行
                    </span>
                  </div>
                  <a className="ghost-button compact-action" href={getDataCenterDownloadUrl(item.key)}>
                    下载 CSV
                  </a>
                </div>
              ))
            ) : (
              <div className="empty-panel">当前没有可下载的数据文件。</div>
            )}
          </div>
        ) : null}
      </div>
    </section>
  );
}

export function Component() {
  const [activeTab, setActiveTab] = useState("全部数据");
  const [datasetKey, setDatasetKey] = useState("");
  const [keyword, setKeyword] = useState("");

  const datasetListState = useApi(getDataCenterDatasets, []);
  const datasets = datasetListState.data?.datasets ?? [];
  const overview = datasetListState.data?.overview;

  const visibleDatasets = useMemo(() => {
    if (activeTab === "全部数据") {
      return datasets;
    }
    return datasets.filter((item) => item.data_type === activeTab);
  }, [activeTab, datasets]);

  useEffect(() => {
    if (activeTab !== "全部数据" && !visibleDatasets.length) {
      setDatasetKey("");
      setKeyword("");
      return;
    }

    const candidates = activeTab === "全部数据" ? datasets : visibleDatasets;
    if (!candidates.length) {
      setDatasetKey("");
      return;
    }
    if (!candidates.some((item) => item.key === datasetKey)) {
      setDatasetKey(candidates[0].key);
      setKeyword("");
    }
  }, [activeTab, datasetKey, datasets, visibleDatasets]);

  const datasetState = useApi<DataCenterDataset | null>(
    () => (datasetKey ? getDataCenterDataset(datasetKey) : Promise.resolve(null)),
    [datasetKey],
  );
  const dataset = datasetState.data;

  const filteredRecords = useMemo(() => {
    const records = dataset?.records ?? [];
    const normalizedKeyword = keyword.trim().toLowerCase();
    if (!normalizedKeyword || !dataset) {
      return records;
    }

    const matchedByColumn = dataset.columns.some((column) => column.toLowerCase().includes(normalizedKeyword));
    return records.filter((row) => {
      if (matchedByColumn) {
        return true;
      }
      return Object.entries(row).some(([column, value]) => {
        return column.toLowerCase().includes(normalizedKeyword) || valueToString(value).toLowerCase().includes(normalizedKeyword);
      });
    });
  }, [dataset, keyword]);

  const missingTypeText = overview?.missing_data_types.length ? overview.missing_data_types.join("、") : "无";
  const showStatus = datasetListState.loading || datasetState.loading || Boolean(datasetListState.error ?? datasetState.error);
  const latestUpdatedAt = formatKpiDateTime(overview?.latest_updated_at);

  return (
    <div className="page-stack data-center-page">
      <section className="filter-card data-center-overview-card">
        <DatasetPicker datasets={activeTab === "全部数据" ? datasets : visibleDatasets} datasetKey={datasetKey} onPick={(key) => { setDatasetKey(key); setKeyword(""); }} />
        <div className="data-center-mode-panel" aria-label="数据中心当前状态">
          <span>当前模式：{overview?.data_mode ?? "无法识别"}</span>
          <span>{overview?.data_source ?? "当前数据来源：项目本地数据文件 / 已缓存数据 / 后端接口返回数据。"}</span>
          <span>格式：{overview?.formats.length ? overview.formats.join(" / ") : "暂无数据"}</span>
        </div>
      </section>

      <div className="stat-grid data-center-stat-grid">
        <StatCard label="数据文件" value={formatNumber(overview?.data_file_count)} trend={`${overview?.scanned_directories.length ?? 0} 个目录已扫描`} />
        <StatCard label="总行数" value={formatNumber(overview?.total_rows)} trend="所有可读数据汇总" tone="green" icon="pulse" />
        <StatCard label="总列数" value={formatNumber(overview?.total_columns)} trend="按数据表列数累计" tone="blue" />
        <StatCard label="已识别表" value={formatNumber(overview?.recognized_table_count)} trend={`缺失：${missingTypeText}`} icon="shield" />
        <StatCard
          label="最近更新"
          value={
            <span className="stat-date-time">
              <span className="stat-date-time-date">{latestUpdatedAt.date}</span>
              {latestUpdatedAt.time ? <span className="stat-date-time-clock">{latestUpdatedAt.time}</span> : null}
            </span>
          }
          trend="来自文件修改时间"
          tone="amber"
          icon="timer"
          className="data-center-updated-card"
          valueTitle={latestUpdatedAt.full}
        />
      </div>

      <section className="data-tabs" aria-label="数据类型">
        {DATA_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={activeTab === tab.key ? "active" : undefined}
            onClick={() => {
              setActiveTab(tab.key);
              setKeyword("");
            }}
          >
            {tab.label}
          </button>
        ))}
      </section>

      <div className="data-center-workspace">
        {showStatus ? (
          <div className="data-center-status">
            <AsyncStatus loading={datasetListState.loading || datasetState.loading} error={datasetListState.error ?? datasetState.error} />
          </div>
        ) : null}
        {activeTab !== "全部数据" && !visibleDatasets.length ? (
          <section className="state-card">当前项目暂未检测到该类原始数据。</section>
        ) : (
          <SourceTable datasets={visibleDatasets} selectedKey={datasetKey} onPick={(key) => { setDatasetKey(key); setKeyword(""); }} />
        )}
        <DatasetDetailPanel
          dataset={dataset}
          allDatasets={datasets}
          keyword={keyword}
          rows={filteredRecords}
          matchedRows={filteredRecords.length}
          onKeywordChange={setKeyword}
        />
      </div>
    </div>
  );
}
