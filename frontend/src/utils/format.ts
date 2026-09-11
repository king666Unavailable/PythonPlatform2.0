function parseDate(value: unknown) {
  if (!value) return null
  const raw = String(value).trim()
  const legacy = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})-(\d{1,2})-(\d{1,2})-(\d{1,2})$/)
  const date = legacy
    ? new Date(Number(legacy[1]), Number(legacy[2]) - 1, Number(legacy[3]), Number(legacy[4]), Number(legacy[5]), Number(legacy[6]))
    : new Date(raw)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value: unknown, fallback = '未设置') {
  const date = parseDate(value)
  if (!date) return value ? String(value) : fallback
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function shortDate(value: unknown, fallback = '不限时') {
  const date = parseDate(value)
  if (!date) return value ? String(value) : fallback
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatDateTimeInput(value: unknown) {
  const date = parseDate(value)
  if (!date) return value ? String(value).replace(/\//g, '-').replace(' ', 'T').slice(0, 16) : ''
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function toApiDateTime(value: unknown) {
  const raw = String(value ?? '').trim().replace(/\//g, '-').replace('T', ' ')
  if (!raw) return ''
  const match = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})$/)
  if (!match) return raw
  const date = new Date(`${match[1]}-${match[2].padStart(2, '0')}-${match[3].padStart(2, '0')}T${match[4].padStart(2, '0')}:${match[5]}`)
  const valid = !Number.isNaN(date.getTime())
    && date.getFullYear() === Number(match[1])
    && date.getMonth() + 1 === Number(match[2])
    && date.getDate() === Number(match[3])
    && date.getHours() === Number(match[4])
    && date.getMinutes() === Number(match[5])
  return valid ? date.toISOString() : raw
}

export function sortAssignmentsByDeadlineDesc<T extends Record<string, unknown>>(items: T[]) {
  return [...items].sort((left, right) => {
    const leftTime = parseDate(left.deadline)?.getTime() ?? Number.NEGATIVE_INFINITY
    const rightTime = parseDate(right.deadline)?.getTime() ?? Number.NEGATIVE_INFINITY
    return rightTime - leftTime
  })
}

const assignmentKindLabels: Record<string, string> = {
  offline: '线下测试',
  classwork: '课堂测试',
  homework: '课后作业',
  mock: '模拟测试',
  exam: '考试',
}

export function assignmentKindLabel(value: unknown) {
  const key = String(value ?? 'homework').trim().toLowerCase()
  return assignmentKindLabels[key] ?? '未设置'
}

export function statusTone(status: string): 'blue' | 'green' | 'orange' | 'gray' | 'red' {
  if (status === '全部开放') return 'green'
  if (status === '部分开放') return 'orange'
  if (status === '暂不开放') return 'red'
  if (status.includes('完成') || status.includes('通过')) return 'green'
  if (status.includes('进行') || status.includes('开放')) return 'blue'
  if (status.includes('待') || status.includes('判')) return 'orange'
  if (status.includes('逾期') || status.includes('失败')) return 'red'
  return 'gray'
}

export function numberValue(value: unknown, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}
