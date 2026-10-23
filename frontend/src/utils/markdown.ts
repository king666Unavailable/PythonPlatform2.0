function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character] ?? character)
}

function inlineMarkdown(value: string): string {
  const unescaped = value.replace(/\\([*_`|])/g, '$1')
  const codeParts: string[] = []
  const withCodePlaceholders = escapeHtml(unescaped).replace(/`([^`\n]+)`/g, (_match, code: string) => {
    const index = codeParts.push(`<code>${code}</code>`) - 1
    return `\u0000${index}\u0000`
  })
  return withCodePlaceholders
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>')
    .replace(/\u0000(\d+)\u0000/g, (_match, index: string) => codeParts[Number(index)] ?? '')
}

function normalizeLines(value: string): string[] {
  return String(value ?? '')
    .replace(/\\([*_`|])/g, '$1')
    .replace(/^(\s*)\\>/gm, '$1>')
    .replace(/\r\n?/g, '\n')
    .split('\n')
}

function tableCells(line: string): string[] {
  let value = line.trim().replace(/\\\s*$/, '')
  if (value.startsWith('|')) value = value.slice(1)
  if (value.endsWith('|')) value = value.slice(0, -1)
  return value.split('|').map((cell) => cell.trim())
}

function isTableSeparator(line: string): boolean {
  const cells = tableCells(line)
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell))
}

function tableAlignment(separator: string): string {
  const cell = separator.trim()
  if (cell.startsWith(':') && cell.endsWith(':')) return 'center'
  if (cell.endsWith(':')) return 'right'
  if (cell.startsWith(':')) return 'left'
  return ''
}

function renderTable(headerLine: string, separatorLine: string, bodyLines: string[]): string {
  const headers = tableCells(headerLine)
  const alignments = tableCells(separatorLine).map(tableAlignment)
  const renderCells = (cells: string[], tag: 'th' | 'td') => headers.map((_header, index) => {
    const alignment = alignments[index]
    const style = alignment ? ` style="text-align:${alignment}"` : ''
    return `<${tag}${style}>${inlineMarkdown(cells[index] ?? '')}</${tag}>`
  }).join('')
  const rows = bodyLines.map((line) => `<tr>${renderCells(tableCells(line), 'td')}</tr>`).join('')
  return `<div class="chat-table-wrap"><table><thead><tr>${renderCells(headers, 'th')}</tr></thead><tbody>${rows}</tbody></table></div>`
}

/** Render the safe Markdown subset commonly emitted by the AI provider. */
export function renderMarkdown(value: string): string {
  const lines = normalizeLines(value)
  const output: string[] = []
  let paragraph: string[] = []
  let list: 'ol' | 'ul' | null = null
  let codeLines: string[] | null = null

  const flushParagraph = () => {
    if (paragraph.length) output.push(`<p>${paragraph.map(inlineMarkdown).join('<br>')}</p>`)
    paragraph = []
  }
  const closeList = () => {
    if (list) output.push(`</${list}>`)
    list = null
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    if (line.trimStart().startsWith('```')) {
      flushParagraph()
      closeList()
      if (codeLines) {
        output.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
        codeLines = null
      } else codeLines = []
      continue
    }
    if (codeLines) {
      codeLines.push(line)
      continue
    }

    const quote = line.match(/^\s{0,3}>\s?(.*)$/)
    if (quote) {
      flushParagraph()
      closeList()
      const quoteLines: string[] = [quote[1].replace(/\\\s*$/, '')]
      while (index + 1 < lines.length) {
        const nextQuote = lines[index + 1].match(/^\s{0,3}>\s?(.*)$/)
        if (!nextQuote) break
        quoteLines.push(nextQuote[1].replace(/\\\s*$/, ''))
        index += 1
      }
      output.push(`<blockquote>${renderMarkdown(quoteLines.join('\n'))}</blockquote>`)
      continue
    }

    if (index + 1 < lines.length && line.includes('|') && isTableSeparator(lines[index + 1])) {
      flushParagraph()
      closeList()
      const separatorLine = lines[index + 1]
      const bodyLines: string[] = []
      index += 2
      while (index < lines.length && lines[index].trim() && lines[index].includes('|')) {
        bodyLines.push(lines[index])
        index += 1
      }
      output.push(renderTable(line, separatorLine, bodyLines))
      index -= 1
      continue
    }

    if (!line.trim()) {
      flushParagraph()
      closeList()
      continue
    }
    const heading = line.match(/^\s{0,3}(#{1,3})\s+(.+)$/)
    if (heading) {
      flushParagraph()
      closeList()
      const level = heading[1].length + 2
      output.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`)
      continue
    }
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/)
    const unordered = line.match(/^\s*[-+*]\s+(.+)$/)
    const item = ordered ?? unordered
    if (item) {
      flushParagraph()
      const nextList = ordered ? 'ol' : 'ul'
      if (list !== nextList) {
        closeList()
        list = nextList
        output.push(`<${list}>`)
      }
      output.push(`<li>${inlineMarkdown(item[1])}</li>`)
      continue
    }
    closeList()
    paragraph.push(line.replace(/\\\s*$/, ''))
  }

  if (codeLines) output.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
  flushParagraph()
  closeList()
  return output.join('')
}
