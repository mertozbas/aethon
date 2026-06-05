/**
 * AETHON Dashboard — Markdown Renderer
 *
 * Lightweight Markdown → HTML converter.
 * Ported from webchat.py's renderMd/inlineMd with enhancements.
 * Supports: headers, bold, italic, strikethrough, code, code blocks, links, lists, hr.
 */

import { esc } from '../theme.js';

/**
 * Render Markdown text to HTML.
 * @param {string} text
 * @returns {string} HTML string
 */
export function renderMarkdown(text) {
  if (!text) return '';

  // Split by fenced code blocks
  const parts = text.split(/(```[\s\S]*?```)/g);
  let html = '';

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];

    if (part.startsWith('```') && part.endsWith('```')) {
      // Fenced code block
      const inner = part.slice(3, -3);
      // Remove optional language hint on first line
      const code = inner.replace(/^[^\n]*\n?/, '');
      html += '<pre><code>' + esc(code) + '</code></pre>';
    } else {
      // Regular text — process line by line
      html += _renderBlock(part);
    }
  }

  return html;
}

function _renderBlock(text) {
  const lines = text.split('\n');
  const rendered = [];
  let inList = false;
  let listType = null; // 'ul' or 'ol'

  for (let j = 0; j < lines.length; j++) {
    const line = lines[j];

    // Heading: # to ######
    const hm = line.match(/^(#{1,6})\s+(.+)$/);
    if (hm) {
      if (inList) { rendered.push(_closeList(listType)); inList = false; }
      const level = hm[1].length;
      rendered.push(`<h${level} style="margin:8px 0;color:var(--accent-primary)">${_inlineMd(hm[2])}</h${level}>`);
      continue;
    }

    // Horizontal rule
    if (/^\s*[-*_]{3,}\s*$/.test(line)) {
      if (inList) { rendered.push(_closeList(listType)); inList = false; }
      rendered.push('<hr style="border-color:var(--border-subtle);margin:8px 0">');
      continue;
    }

    // Unordered list: - item, * item
    const ulMatch = line.match(/^\s*[-*+]\s+(.+)$/);
    if (ulMatch) {
      if (!inList || listType !== 'ul') {
        if (inList) rendered.push(_closeList(listType));
        rendered.push('<ul style="margin:4px 0;padding-left:20px">');
        inList = true;
        listType = 'ul';
      }
      rendered.push('<li>' + _inlineMd(ulMatch[1]) + '</li>');
      continue;
    }

    // Ordered list: 1. item
    const olMatch = line.match(/^\s*\d+\.\s+(.+)$/);
    if (olMatch) {
      if (!inList || listType !== 'ol') {
        if (inList) rendered.push(_closeList(listType));
        rendered.push('<ol style="margin:4px 0;padding-left:20px">');
        inList = true;
        listType = 'ol';
      }
      rendered.push('<li>' + _inlineMd(olMatch[1]) + '</li>');
      continue;
    }

    // Blockquote: > text
    const bq = line.match(/^>\s?(.*)$/);
    if (bq) {
      if (inList) { rendered.push(_closeList(listType)); inList = false; }
      rendered.push(`<blockquote style="border-left:2px solid var(--accent-primary);padding-left:10px;margin:4px 0;color:var(--text-secondary)">${_inlineMd(bq[1])}</blockquote>`);
      continue;
    }

    // Empty line
    if (line.trim() === '') {
      if (inList) { rendered.push(_closeList(listType)); inList = false; }
      rendered.push('<br>');
      continue;
    }

    // Normal text
    if (inList) { rendered.push(_closeList(listType)); inList = false; }
    rendered.push(_inlineMd(line));
    if (j < lines.length - 1) rendered.push('<br>');
  }

  if (inList) { rendered.push(_closeList(listType)); }

  return rendered.join('');
}

function _closeList(type) {
  return type === 'ol' ? '</ol>' : '</ul>';
}

/**
 * Render inline Markdown.
 * @param {string} t
 * @returns {string}
 */
function _inlineMd(t) {
  // Protect inline code first
  const codes = [];
  t = t.replace(/`([^`]+)`/g, (_, c) => {
    codes.push('<code>' + esc(c) + '</code>');
    return '\x00C' + (codes.length - 1);
  });

  // Escape HTML in remaining text (not inside code placeholders)
  const segs = t.split(/(\x00C\d+)/g);
  let out = '';
  for (let i = 0; i < segs.length; i++) {
    if (/^\x00C\d+$/.test(segs[i])) {
      out += segs[i];
    } else {
      out += esc(segs[i]);
    }
  }
  t = out;

  // Bold: **text** or __text__
  t = t.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  t = t.replace(/__(.+?)__/g, '<b>$1</b>');

  // Italic: *text* or _text_ (not inside words)
  t = t.replace(/(^|[\s(])\*([^*]+?)\*(?=[\s).,!?]|$)/g, '$1<i>$2</i>');
  t = t.replace(/(^|[\s(])_([^_]+?)_(?=[\s).,!?]|$)/g, '$1<i>$2</i>');

  // Strikethrough: ~~text~~
  t = t.replace(/~~(.+?)~~/g, '<s>$1</s>');

  // Links: [text](url)
  t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Restore inline code
  for (let i = 0; i < codes.length; i++) {
    t = t.replace('\x00C' + i, codes[i]);
  }

  return t;
}
