import { Fragment, type ReactNode } from 'react';
import { safeUrl } from '../../utils/chatbotUtils';

/**
 * Tiny, dependency-free renderer for: paragraphs, "- " bullets, "1. " lists, **bold**, [links](https://...).
 * Builds React nodes (no dangerouslySetInnerHTML). To get full markdown later, swap this one component
 * for react-markdown + rehype-sanitize; ChatMessage will not need to change.
 */
function renderInline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g).filter(Boolean).map((part, i) => {
    const bold = part.match(/^\*\*([^*]+)\*\*$/);
    if (bold) return <strong key={i}>{bold[1]}</strong>;
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      const href = safeUrl(link[2]);
      return href ? <a key={i} href={href} target="_blank" rel="noopener noreferrer">{link[1]}</a> : <Fragment key={i}>{link[1]}</Fragment>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

export function RichText({ text }: { text: string }) {
  const nodes: ReactNode[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flushParagraph = () => {
    if (paragraph.length) nodes.push(<p key={nodes.length}>{paragraph.map((l, i) => <Fragment key={i}>{i > 0 && <br />}{renderInline(l)}</Fragment>)}</p>);
    paragraph = [];
  };
  const flushList = () => {
    if (!list) return;
    const Tag = list.ordered ? 'ol' : 'ul';
    nodes.push(<Tag key={nodes.length}>{list.items.map((it, i) => <li key={i}>{renderInline(it)}</li>)}</Tag>);
    list = null;
  };

  for (const line of text.split('\n')) {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const item = bullet ?? numbered;
    if (item) {
      flushParagraph();
      const ordered = !bullet;
      if (list && list.ordered !== ordered) flushList();
      list = list ?? { ordered, items: [] };
      list.items.push(item[1]);
    } else if (!line.trim()) { flushParagraph(); flushList(); }
    else { flushList(); paragraph.push(line); }
  }
  flushParagraph();
  flushList();
  return <div className="cb-rich">{nodes}</div>;
}
