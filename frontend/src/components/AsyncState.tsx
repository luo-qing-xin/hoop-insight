import { COMMON_COPY } from "../constants/zhLabels";

type AsyncStatusProps = {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
};

export function AsyncStatus({ loading, error, empty, emptyMessage = COMMON_COPY.noData }: AsyncStatusProps) {
  if (loading) {
    return <div className="state-card">{COMMON_COPY.loading}</div>;
  }

  if (error) {
    return <div className="state-card state-card-error">{COMMON_COPY.loadFailed}：{error}</div>;
  }

  if (empty) {
    return <div className="state-card">{emptyMessage}</div>;
  }

  return null;
}
