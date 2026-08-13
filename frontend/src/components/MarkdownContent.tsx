import { useMemo, type ReactNode } from "react";
import { translateKnownNamesInText } from "../utils/nameTranslations";

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

export default function MarkdownContent({ content, className = "markdown-answer" }: { content: string; className?: string }) {
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

  return <div className={className}>{blocks}</div>;
}
