import type { ReactNode } from "react";

/**
 * Renders document Markdown safely. The text is turned into React elements directly, never into HTML,
 * so a document cannot inject markup or scripts. Supported: headings, paragraphs, bullet and numbered
 * lists, quotes, code blocks, horizontal rules, `code`, **bold**, *italic* and [links](https://…).
 * Links are only followed for http(s) and mailto addresses.
 */

const SAFE_LINK = /^(https?:\/\/|mailto:)/i;
const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*|_[^_\s][^_]*_)|(\[[^\]]+\]\([^)\s]+\))/g;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let index = 0;
  for (const match of text.matchAll(INLINE)) {
    const start = match.index ?? 0;
    if (start > last) nodes.push(text.slice(last, start));
    const token = match[0];
    const key = `${keyPrefix}-${index++}`;
    if (match[1]) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (match[2]) {
      nodes.push(<strong key={key}>{renderInline(token.slice(2, -2), key)}</strong>);
    } else if (match[3]) {
      nodes.push(<em key={key}>{renderInline(token.slice(1, -1), key)}</em>);
    } else {
      const [, label, href] = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(token) ?? [];
      nodes.push(
        href && SAFE_LINK.test(href) ? (
          <a key={key} href={href} target="_blank" rel="noopener noreferrer nofollow">{label}</a>
        ) : (
          <span key={key}>{label ?? token}</span>
        ),
      );
    }
    last = start + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; lines: string[] }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "quote"; lines: string[] }
  | { type: "code"; text: string }
  | { type: "rule" };

export function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    if (line.trimStart().startsWith("```")) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trimStart().startsWith("```")) code.push(lines[i++]);
      i++; // closing fence (or end of text)
      blocks.push({ type: "code", text: code.join("\n") });
      continue;
    }
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      i++;
      continue;
    }
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) {
      blocks.push({ type: "rule" });
      i++;
      continue;
    }
    const bullet = /^\s*[-*+]\s+/;
    const numbered = /^\s*\d+[.)]\s+/;
    if (bullet.test(line) || numbered.test(line)) {
      const ordered = numbered.test(line);
      const pattern = ordered ? numbered : bullet;
      const items: string[] = [];
      while (i < lines.length && pattern.test(lines[i])) items.push(lines[i++].replace(pattern, ""));
      blocks.push({ type: "list", ordered, items });
      continue;
    }
    if (line.startsWith(">")) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].startsWith(">")) quote.push(lines[i++].replace(/^>\s?/, ""));
      blocks.push({ type: "quote", lines: quote });
      continue;
    }
    const paragraph: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,6})\s/.test(lines[i]) &&
      !lines[i].trimStart().startsWith("```") &&
      !bullet.test(lines[i]) &&
      !numbered.test(lines[i]) &&
      !lines[i].startsWith(">")
    ) {
      paragraph.push(lines[i++]);
    }
    blocks.push({ type: "paragraph", lines: paragraph });
  }
  return blocks;
}

function withBreaks(lines: string[], key: string): ReactNode[] {
  return lines.flatMap((line, i) => (i === 0 ? renderInline(line, `${key}-${i}`) : [<br key={`${key}-br-${i}`} />, ...renderInline(line, `${key}-${i}`)]));
}

export function MarkdownView({ source, empty = "This document is empty." }: { source: string; empty?: string }) {
  const blocks = parseMarkdown(source);
  if (blocks.length === 0) return <p className="muted-text">{empty}</p>;
  return (
    <div className="markdown-body">
      {blocks.map((block, i) => {
        const key = `b${i}`;
        switch (block.type) {
          case "heading": {
            const level = Math.min(block.level + 1, 6); // the page/dialog already has an h1/h2
            const Tag = `h${level}` as "h2" | "h3" | "h4" | "h5" | "h6";
            return <Tag key={key}>{renderInline(block.text, key)}</Tag>;
          }
          case "list": {
            const items = block.items.map((item, j) => <li key={`${key}-${j}`}>{renderInline(item, `${key}-${j}`)}</li>);
            return block.ordered ? <ol key={key}>{items}</ol> : <ul key={key}>{items}</ul>;
          }
          case "quote":
            return <blockquote key={key}>{withBreaks(block.lines, key)}</blockquote>;
          case "code":
            return <pre key={key}><code>{block.text}</code></pre>;
          case "rule":
            return <hr key={key} />;
          default:
            return <p key={key}>{withBreaks(block.lines, key)}</p>;
        }
      })}
    </div>
  );
}
