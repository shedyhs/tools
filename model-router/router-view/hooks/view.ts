// Pure helpers for the router pane, kept apart so the tests can reach them.
export type Doubt = {
  ts: string
  confidence: number
  jev: string
  prompt?: string
}

export type Summary = {
  since: string
  total: number
  final: Record<string, number>
  jev: Record<string, number>
  doubts: Doubt[]
  failed: number
  rejects: number
  ms_median: number | null
  ms_max: number | null
  confidence_min: number
  fallback: string
  // Absent when the router predates the effort feature.
  effort?: Record<string, number>
  effort_default?: number
}

export const BAR_WIDTH = 12

// A bar of BAR_WIDTH cells: filled for n out of total, the rest light.
export function bar(n: number, total: number): [string, string] {
  const full = total > 0 ? Math.round((n * BAR_WIDTH) / total) : 0

  return ['█'.repeat(full), '░'.repeat(BAR_WIDTH - full)]
}

export function percent(n: number, total: number): string {
  return `${total > 0 ? Math.round((n * 100) / total) : 0}%`.padStart(4)
}

export function clip(text: string, width: number): string {
  return text.length > width ? `${text.slice(0, width - 1)}…` : text
}

export type AgentNode = {
  id: string
  parentId?: string
  type: string
  description: string
  name?: string
  status: string
}

export type AgentRow = { prefix: string; agent: AgentNode }

const ENDED = new Set(['completed', 'failed', 'killed'])

// The active agents as tree rows. An ended agent stays only while an active one
// hangs below it. An agent whose parent is gone becomes a root.
export function agentRows(agents: readonly AgentNode[]): AgentRow[] {
  const byId = new Map(agents.map(a => [a.id, a]))
  const kids = new Map<string | undefined, AgentNode[]>()
  for (const a of agents) {
    const key = a.parentId !== undefined && byId.has(a.parentId) ? a.parentId : undefined
    kids.set(key, [...(kids.get(key) ?? []), a])
  }
  const isLive = (a: AgentNode): boolean =>
    !ENDED.has(a.status) || (kids.get(a.id) ?? []).some(isLive)

  const rows: AgentRow[] = []
  const walk = (parent: string | undefined, indent: string) => {
    const list = (kids.get(parent) ?? []).filter(isLive)
    list.forEach((agent, i) => {
      const isLast = i === list.length - 1
      rows.push({ prefix: `${indent}${isLast ? '└─' : '├─'}`, agent })
      walk(agent.id, `${indent}${isLast ? '  ' : '│ '}`)
    })
  }
  walk(undefined, '')

  return rows
}

// The short name of the model an agent runs on: haiku, sonnet or opus. Any
// other model shows its last part, so a new family still reads.
export function modelTag(model: string | undefined): string {
  if (!model) return '?'
  const family = model.toLowerCase().match(/haiku|sonnet|opus/)?.[0]
  return family ?? model.split('-').pop() ?? model
}

// The efforts used, as 'low 3 · high 10 · padrão (high) 2'. 'padrão' counts the turns
// where Jev was not sure, so the default (high) was used. Efforts with no turn are left out.
export function effortLine(
  effort: Record<string, number> | undefined,
  defaults: number | undefined,
): string {
  const parts = Object.entries(effort ?? {})
    .filter(([, n]) => n > 0)
    .map(([name, n]) => `${name} ${n}`)
  if (defaults) parts.push(`padrão (high) ${defaults}`)

  return parts.length > 0 ? parts.join(' · ') : 'nenhum ainda'
}
