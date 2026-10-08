import type { Register } from 'claude-code'

import { agentRows, bar, clip, effortLine, modelTag, percent, type Summary } from './view'

const PANE = 'router-view'
const PANE_OPEN = { id: PANE, title: 'Model router', columns: 36 }
const REFRESH_MS = 5000
const STATS_ARGV = ['claude-model-router', '--stats-json', 'today']
const DOUBTS_SHOWN = 5
const PROMPT_WIDTH = 30
const PANE_COLUMNS = 36
const STATUS_LOOK: Record<string, { glyph: string; color?: string }> = {
  running: { glyph: '●', color: 'success' },
  waiting: { glyph: '◐', color: 'warning' },
  pending: { glyph: '○' },
  idle: { glyph: '◌' },
}
const TIER_COLOR: Record<string, string> = {
  haiku: 'success',
  sonnet: 'suggestion',
  opus: 'claude',
}

// Each agent's model, by agent id, set when it spawns. A reload clears it, so
// an agent started before that shows '?'.
const modelOf = new Map<string, string>()

// Which sections show their body. Both start folded; a reload folds them again.
let expanded = { agents: false, jev: false }

export const register: Register = on => {
  on('agent.spawn', async ($, e, next) => {
    const started = await next(e)
    if (started.deny === undefined && started.agentId) {
      modelOf.set(started.agentId, started.model)
    }

    return started
  })

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'router',
      description: 'Show how the model router sent the turns (Haiku, Sonnet, Opus)',
    })
    // Unasked, the dock opens only from 144 terminal columns. /router opens it at any width.
    void $.ui.open(PANE_OPEN)
    $.clock.every(REFRESH_MS, () => $.ui.invalidate('ui.render'))

    return next(e)
  })

  on('command.run', { command: 'router' }, async $ => {
    await $.ui.open(PANE_OPEN)

    return { text: 'Model router pane opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const toggle = (section: keyof typeof expanded) => () => {
      expanded = { ...expanded, [section]: !expanded[section] }
      $.ui.invalidate('ui.render')
    }
    const arrow = (isOpen: boolean) => (isOpen ? '▾' : '▸')
    const ran = await $.process
      .run(STATS_ARGV, { timeoutMs: 10_000 })
      .catch(error => ({ exitCode: -1, stdout: '', stderr: String(error) }))
    let s: Summary
    try {
      if (ran.exitCode !== 0) throw new Error(ran.stderr)
      s = JSON.parse(ran.stdout)
    } catch (error) {
      return <Text color="error">Router stats failed: {clip(String(error), 200)}</Text>
    }

    const rows = agentRows(await $.agent.list().catch(() => []))
    const tiers = Object.keys(s.final)
    const doubts = s.doubts.slice(-DOUBTS_SHOWN).reverse()

    return (
      <Box flexDirection="column">
        <Button
          plain
          label={`${arrow(expanded.agents)} Agentes ativos (${rows.length})`}
          onPress={toggle('agents')}
        />
        {expanded.agents && <Text dimColor>main</Text>}
        {expanded.agents && rows.length === 0 && <Text dimColor>└─ nenhum subagente</Text>}
        {expanded.agents && rows.map(({ prefix, agent }) => {
          const look = STATUS_LOOK[agent.status] ?? { glyph: '·' }
          const tag = `[${modelTag(modelOf.get(agent.id))}] `
          const room = PANE_COLUMNS - prefix.length - 3 - tag.length
          return (
            <Text>
              <Text dimColor>{prefix} </Text>
              <Text color={look.color}>{look.glyph} </Text>
              <Text color={TIER_COLOR[modelTag(modelOf.get(agent.id))]}>{tag}</Text>
              <Text>{clip(`${agent.type}: ${agent.description || agent.name || ''}`, room)}</Text>
            </Text>
          )
        })}
        <Text> </Text>
        <Text dimColor>{'─'.repeat(PANE_COLUMNS - 4)}</Text>
        <Text> </Text>

        <Button
          plain
          label={`${arrow(expanded.jev)} Jev hoje · ${s.total} turnos`}
          onPress={toggle('jev')}
        />
        {expanded.jev && (
          <Box flexDirection="column">
            <Text> </Text>
            {tiers.map(tier => {
              const [full, empty] = bar(s.final[tier], s.total)
              return (
                <Text>
                  <Text color={TIER_COLOR[tier]}>{tier.padEnd(7)}</Text>
                  <Text color={TIER_COLOR[tier]}>{full}</Text>
                  <Text dimColor>{empty}</Text>
                  <Text> {String(s.final[tier]).padStart(3)}</Text>
                  <Text dimColor>{percent(s.final[tier], s.total)}</Text>
                </Text>
              )
            })}
            <Text dimColor>
              Jev pediu: {tiers.map(t => `${t[0].toUpperCase()} ${s.jev[t]}`).join(' · ')}
            </Text>
            <Text dimColor>Esforço: {effortLine(s.effort, s.effort_default)}</Text>
            <Text> </Text>

            <Text bold>Fallback para {s.fallback}</Text>
            <Text>
              <Text dimColor>{'dúvida'.padEnd(9)}</Text>
              <Text color={s.doubts.length ? 'warning' : undefined}>{s.doubts.length}</Text>
              <Text dimColor>  (conf {'<'} {s.confidence_min})</Text>
            </Text>
            <Text>
              <Text dimColor>{'falha'.padEnd(9)}</Text>
              <Text color={s.failed ? 'error' : undefined}>{s.failed}</Text>
            </Text>
            <Text>
              <Text dimColor>{'400'.padEnd(9)}</Text>
              <Text color={s.rejects ? 'error' : undefined}>{s.rejects}</Text>
            </Text>
            {s.ms_median !== null && (
              <Text>
                <Text dimColor>{'latência'.padEnd(9)}</Text>
                <Text>{s.ms_median} ms</Text>
                <Text dimColor>  (máx {s.ms_max})</Text>
              </Text>
            )}

            {doubts.length > 0 && <Text> </Text>}
            {doubts.length > 0 && <Text bold>Dúvidas recentes</Text>}
            {doubts.map(d => (
              <Box flexDirection="column">
                <Text>
                  <Text dimColor>{d.ts.slice(-5)} </Text>
                  <Text color="warning">{d.confidence.toFixed(2)}</Text>
                  <Text dimColor> jev→</Text>
                  <Text color={TIER_COLOR[d.jev]}>{d.jev}</Text>
                </Text>
                <Text dimColor wrap="truncate-end">  {clip(d.prompt ?? '', PROMPT_WIDTH)}</Text>
              </Box>
            ))}
          </Box>
        )}
      </Box>
    )
  })
}
