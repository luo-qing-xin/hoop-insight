import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ApiError, askAI, type AskAiResponse } from "../api/client";
import { AI_COPY, DATA_TYPE_LABELS } from "../constants/zhLabels";
import { translateKnownNamesInText } from "../utils/nameTranslations";

type AskHistoryItem = {
  id: number;
  question: string;
  response: AskAiResponse;
  unconfigured: boolean;
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

function isAIUnconfiguredText(value: unknown) {
  if (typeof value !== "string") {
    return false;
  }

  const text = value.toLowerCase();
  return text.includes("未配置") || text.includes("没有配置") || text.includes("not configured") || text.includes("missing api key") || text.includes("llm") || text.includes("api key");
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const segments = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);

  return segments.map((segment, index) => {
    if (segment.startsWith("**") && segment.endsWith("**")) {
      return <strong key={index}>{segment.slice(2, -2)}</strong>;
    }
    if (segment.startsWith("`") && segment.endsWith("`")) {
      return <code key={index}>{segment.slice(1, -1)}</code>;
    }
    return segment;
  });
}

function MarkdownCard({ content }: { content: string }) {
  const blocks = useMemo(() => {
    const lines = translateKnownNamesInText(content).trim().split(/\r?\n/);
    const rendered: ReactNode[] = [];
    let listItems: string[] = [];

    function flushList() {
      if (listItems.length === 0) {
        return;
      }

      rendered.push(
        <ul key={`list-${rendered.length}`}>
          {listItems.map((item, index) => (
            <li key={`${item}-${index}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>,
      );
      listItems = [];
    }

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        return;
      }

      const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushList();
        const level = Math.min(heading[1].length, 3);
        const headingContent = renderInlineMarkdown(heading[2]);
        if (level === 1) {
          rendered.push(<h3 key={`heading-${rendered.length}`}>{headingContent}</h3>);
        } else if (level === 2) {
          rendered.push(<h4 key={`heading-${rendered.length}`}>{headingContent}</h4>);
        } else {
          rendered.push(<h5 key={`heading-${rendered.length}`}>{headingContent}</h5>);
        }
        return;
      }

      const listItem = trimmed.match(/^[-*]\s+(.+)$/) ?? trimmed.match(/^\d+\.\s+(.+)$/);
      if (listItem) {
        listItems.push(listItem[1]);
        return;
      }

      flushList();
      rendered.push(<p key={`p-${rendered.length}`}>{renderInlineMarkdown(trimmed)}</p>);
    });

    flushList();
    return rendered;
  }, [content]);

  return <div className="markdown-answer">{blocks}</div>;
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

            return (
              <article key={item.id} className="answer-card">
                <div className="answer-card-top">
                  <div>
                    <span>{AI_COPY.questionLabel}</span>
                    <h2>{item.question}</h2>
                  </div>
                  <small>{item.response.confidence ?? AI_COPY.confidenceFallback}</small>
                </div>

                {dataTypes.length > 0 ? (
                  <div className="data-type-list" aria-label={AI_COPY.dataTypeAria}>
                    {dataTypes.map((type) => (
                      <span key={type}>{type}</span>
                    ))}
                  </div>
                ) : null}

                {item.unconfigured ? <div className="state-card ask-config-card">{AI_COPY.unconfiguredAnswer}</div> : null}
                <MarkdownCard content={answer} />
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
