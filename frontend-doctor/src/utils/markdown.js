import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({
  gfm: true,
  breaks: true
})

/**
 * 将 Markdown 转为可安全插入页面的 HTML（用于医生端只读展示）。
 * @param {string | null | undefined} text
 * @returns {string}
 */
export function renderMarkdownToSafeHtml(text) {
  if (text === null || text === undefined || text === '') {
    return ''
  }
  const raw = marked.parse(String(text))
  return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } })
}
