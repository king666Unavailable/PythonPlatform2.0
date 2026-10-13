const configuredThemeOrder = [
  'Python语法基础',
  '程序控制结构',
  '函数和代码复用',
  'Python基本数据结构',
  '类（面向对象）',
  '字符串、正则表达式和文件',
  'NumPy库',
  'Pandas',
  'Pandas进阶',
  'matplotlib',
  '时间序列',
]

const themeRank = new Map(configuredThemeOrder.map((title, index) => [title, index]))

export function compareThemeTitles(left: string, right: string, leftSortOrder?: number | null, rightSortOrder?: number | null): number {
  if (typeof leftSortOrder === 'number' && typeof rightSortOrder === 'number' && leftSortOrder !== rightSortOrder) {
    return leftSortOrder - rightSortOrder
  }
  const leftRank = themeRank.get(left)
  const rightRank = themeRank.get(right)

  if (leftRank !== undefined && rightRank !== undefined) return leftRank - rightRank
  if (leftRank !== undefined) return -1
  if (rightRank !== undefined) return 1
  return left.localeCompare(right, 'zh-CN')
}
