'use client'

import { useEffect, useRef } from 'react'

// Inline markdown inline parser (bold, italics, line breaks)
function renderInline(content) {
  if (!content) return '';
  const parts = content.split(/(<br\s*\/?>|\*\*[^*]+\*\*|\*[^*]+\*)/gi);
  return parts.map((part, j) => {
    if (part.toLowerCase().startsWith('<br')) {
      return <br key={j} />;
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={j}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={j} style={{ color: '#4F46E5', fontStyle: 'normal', fontWeight: 600 }}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

// Preprocessor to combine wrapped table rows
function preprocessLines(lines) {
  const result = [];
  for (let i = 0; i < lines.length; i++) {
    let current = lines[i];

    // Check if the current line starts with '|' and merge with subsequent wrapped table lines
    while (i + 1 < lines.length) {
      const next = lines[i + 1];
      const curTrim = current.trim();
      const nextTrim = next.trim();

      const currentStarts = curTrim.startsWith('|');
      const currentEnds = curTrim.endsWith('|');
      const nextStarts = nextTrim.startsWith('|');
      const nextEnds = nextTrim.endsWith('|');
      const nextHasPipe = nextTrim.includes('|');

      let shouldMerge = false;
      if (currentStarts) {
        if (!currentEnds && nextHasPipe) {
          shouldMerge = true;
        } else if (!nextStarts && nextEnds) {
          shouldMerge = true;
        } else if (curTrim.includes('|-') && !nextStarts && nextTrim.includes('-|')) {
          shouldMerge = true;
        }
      }

      if (shouldMerge) {
        // Join separator lines directly, others with space
        if (curTrim.endsWith('-') && nextTrim.startsWith('-')) {
          current = current + nextTrim;
        } else {
          if (current.endsWith(' ') || next.startsWith(' ')) {
            current = current + next;
          } else {
            current = current + ' ' + next;
          }
        }
        i++; // Consume the merged line
      } else {
        break;
      }
    }
    result.push(current);
  }
  return result;
}

// Table block parser
function parseTable(tableLines, blockKey) {
  if (tableLines.length < 2) {
    return tableLines.map((line, idx) => <div key={`${blockKey}-${idx}`} className="md">{line}</div>);
  }

  // Helper to split table row by | and clean up empty cells
  const getCells = (rowLine) => {
    let cells = rowLine.split('|').map(s => s.trim());
    if (cells[0] === '') cells.shift();
    if (cells[cells.length - 1] === '') cells.pop();
    return cells;
  };

  const headers = getCells(tableLines[0]);
  const isSeparator = /^[|\s:-]+$/.test(tableLines[1]);
  const startIdx = isSeparator ? 2 : 1;
  const rows = [];

  for (let k = startIdx; k < tableLines.length; k++) {
    const cells = getCells(tableLines[k]);
    if (cells.length > 0) {
      // Pad or truncate row cells to align with headers
      while (cells.length < headers.length) {
        cells.push('');
      }
      if (cells.length > headers.length) {
        cells.length = headers.length;
      }
      rows.push(cells);
    }
  }

  return (
    <div key={blockKey} className="premium-table-container">
      <table className="premium-table">
        <thead>
          <tr>
            {headers.map((h, idx) => (
              <th key={idx}>{renderInline(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rIdx) => (
            <tr key={rIdx}>
              {row.map((cell, cIdx) => (
                <td key={cIdx}>{renderInline(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Helper to automatically bold the title in lists (e.g. "AI/ML Bootcamp - ₹12,999" -> "**AI/ML Bootcamp** - ₹12,999")
function autoBoldTitle(text) {
  if (text.includes('**')) return text;
  const splitters = [' - ', ' : ', ': '];
  for (const s of splitters) {
    const idx = text.indexOf(s);
    if (idx > 0) {
      const title = text.slice(0, idx);
      const rest = text.slice(idx);
      return `**${title}**${rest}`;
    }
  }
  return text;
}

// Main markdown parser (block-level parsing)
function renderMd(text) {
  if (!text) return null;
  const lines = preprocessLines(text.split('\n'));
  const elements = [];
  let tableLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const isTableLine = line.trim().startsWith('|');

    if (isTableLine) {
      tableLines.push(line);
    } else {
      if (tableLines.length > 0) {
        elements.push(parseTable(tableLines, elements.length));
        tableLines = [];
      }

      const trimmed = line.trim();

      // Empty line -> render vertical space
      if (!trimmed) {
        elements.push(<div key={elements.length} style={{ height: 10 }} />);
        continue;
      }

      // Check for headers: #, ##, ###
      if (trimmed.startsWith('### ')) {
        const content = trimmed.slice(4);
        elements.push(
          <h4 key={elements.length} style={{ fontSize: 13.5, fontWeight: 800, color: '#0A0A0F', margin: '14px 0 6px 0', letterSpacing: '-0.01em' }}>
            {renderInline(content)}
          </h4>
        );
        continue;
      }
      if (trimmed.startsWith('## ')) {
        const content = trimmed.slice(3);
        elements.push(
          <h3 key={elements.length} style={{ fontSize: 15, fontWeight: 800, color: '#0A0A0F', margin: '18px 0 8px 0', letterSpacing: '-0.02em' }}>
            {renderInline(content)}
          </h3>
        );
        continue;
      }
      if (trimmed.startsWith('# ')) {
        const content = trimmed.slice(2);
        elements.push(
          <h2 key={elements.length} style={{ fontSize: 17, fontWeight: 800, color: '#0A0A0F', margin: '22px 0 10px 0', letterSpacing: '-0.02em' }}>
            {renderInline(content)}
          </h2>
        );
        continue;
      }

      // Check for bullet lists (handles standard prefix: -, •, *)
      const isBullet = trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ');

      // Check for leading emoji list item (e.g. "🚀 AI/ML Bootcamp")
      const emojiMatch = trimmed.match(/^([\u{1F300}-\u{1F9FF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|\p{Emoji_Presentation})\s*/u);

      if (isBullet) {
        const leadingSpaces = line.length - line.trimStart().length;
        const indentLevel = Math.floor(leadingSpaces / 2);
        let content = trimmed.slice(2);

        // Auto-bold the list title
        content = autoBoldTitle(content);
        const rendered = renderInline(content);

        elements.push(
          <div
            key={elements.length}
            className="md list-item"
            style={{
              display: 'flex',
              gap: 8,
              alignItems: 'flex-start',
              margin: '8px 0',
              paddingLeft: indentLevel * 16
            }}
          >
            <span className="md list-bullet" style={{ color: '#4F46E5', fontWeight: 'bold', fontSize: 14, lineHeight: '1.2' }}>·</span>
            <span style={{ fontSize: 13.5, color: '#2D3748', lineHeight: '1.6' }}>{rendered}</span>
          </div>
        );
        continue;
      } else if (emojiMatch) {
        const leadingSpaces = line.length - line.trimStart().length;
        const indentLevel = Math.floor(leadingSpaces / 2);
        const emoji = emojiMatch[1];
        let content = trimmed.slice(emojiMatch[0].length);

        // Auto-bold the list title
        content = autoBoldTitle(content);
        const rendered = renderInline(content);

        elements.push(
          <div
            key={elements.length}
            className="md list-item"
            style={{
              display: 'flex',
              gap: 10,
              alignItems: 'flex-start',
              margin: '10px 0',
              paddingLeft: indentLevel * 16
            }}
          >
            <span style={{ fontSize: 15, lineHeight: '1.2', flexShrink: 0 }}>{emoji}</span>
            <span style={{ fontSize: 13.5, color: '#2D3748', lineHeight: '1.6' }}>{rendered}</span>
          </div>
        );
        continue;
      }

      // Regular paragraph
      const rendered = renderInline(line);
      elements.push(
        <div key={elements.length} className="md" style={{ margin: '8px 0', fontSize: 13.5, color: '#2D3748', lineHeight: '1.6' }}>
          {rendered}
        </div>
      );
    }
  }

  if (tableLines.length > 0) {
    elements.push(parseTable(tableLines, elements.length));
  }

  return elements;
}

const SENTIMENT_META = {
  positive:   { color: '#10B981', bg: '#ECFDF5', border: '#A7F3D0', label: 'Positive' },
  neutral:    { color: '#6366F1', bg: '#EEF2FF', border: '#C7D2FE', label: 'Neutral' },
  confused:   { color: '#F59E0B', bg: '#FFFBEB', border: '#FDE68A', label: 'Needs clarity' },
  frustrated: { color: '#F43F5E', bg: '#FFF1F2', border: '#FECDD3', label: 'Frustrated' },
}

export default function MessageBubble({ message, studentName, isLatest }) {
  const ref = useRef(null)
  const isBot = message.role === 'bot'
  const sm = SENTIMENT_META[message.sentiment] || SENTIMENT_META.neutral

  useEffect(() => {
    if (isLatest) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [isLatest])

  const ts = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    : null

  if (isBot) {
    return (
      <div ref={ref} className={isLatest ? 'anim-fade-up' : ''} style={s.botRow}>
        <div style={s.botAvatar}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5"/>
          </svg>
        </div>
        <div style={{ maxWidth: 'min(520px, calc(100% - 44px))', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={s.botLabel}>EduFlow AI</div>
          <div style={s.botBubble}>
            <div style={{ fontSize: 14, lineHeight: 1.7, color: '#1E1E2E' }}>
              {renderMd(message.content)}
            </div>
          </div>
          {ts && <span style={s.timestamp}>{ts}</span>}
        </div>
      </div>
    )
  }

  return (
    <div ref={ref} className={isLatest ? 'anim-fade-up' : ''} style={s.userRow}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end', maxWidth: 'min(460px, calc(100% - 44px))' }}>
        <div style={s.userBubble}>
          <span style={{ fontSize: 14, lineHeight: 1.65, color: '#fff' }}>{message.content}</span>
        </div>
        {ts && <span style={{ ...s.timestamp, textAlign: 'right' }}>{ts}</span>}
      </div>
      <div style={s.userAvatar}>
        <span style={{ fontSize: 11, fontWeight: 800, color: '#4F46E5' }}>
          {(studentName || 'U')[0].toUpperCase()}
        </span>
      </div>
    </div>
  )
}

export function TypingIndicator() {
  return (
    <div style={s.botRow} className="anim-fade-in">
      <div style={s.botAvatar}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5"/>
        </svg>
      </div>
      <div style={{ ...s.botBubble, padding: '10px 14px', maxWidth: 80 }}>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', height: 16 }}>
          <span className="dot-typing" />
          <span className="dot-typing" />
          <span className="dot-typing" />
        </div>
      </div>
    </div>
  )
}

const s = {
  botRow: {
    display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 10,
  },
  botAvatar: {
    width: 32, height: 32, borderRadius: 12, flexShrink: 0,
    background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
    border: '1px solid #C7D2FE',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(79,70,229,0.12)',
  },
  botLabel: {
    fontSize: 11, fontWeight: 700, color: '#6366F1',
    letterSpacing: '0.05em', textTransform: 'uppercase', paddingLeft: 2, marginBottom: 2,
  },
  botBubble: {
    background: '#FFFFFF',
    border: '1px solid rgba(0,0,0,0.08)',
    borderRadius: '4px 20px 20px 20px',
    padding: '10px 14px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
  },
  userRow: {
    display: 'flex', gap: 10, alignItems: 'flex-start',
    justifyContent: 'flex-end', marginBottom: 10,
  },
  userBubble: {
    background: 'linear-gradient(135deg, #4F46E5, #6366F1)',
    borderRadius: '20px 4px 20px 20px',
    padding: '10px 14px',
    boxShadow: '0 4px 16px rgba(79,70,229,0.25)',
  },
  userAvatar: {
    width: 32, height: 32, borderRadius: 12, flexShrink: 0,
    background: '#EEF2FF', border: '1px solid #C7D2FE',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  timestamp: {
    fontSize: 11, color: '#94A3B8', paddingLeft: 2,
  },
}
