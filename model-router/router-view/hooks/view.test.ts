import { expect, test } from 'claude-code/testing'

import { BAR_WIDTH, bar, clip, effortLine, percent } from './view'

test('bar fills its share and keeps a fixed width', async () => {
  const [full, empty] = bar(9, 14)
  expect(full.length).toBe(8)
  expect(full.length + empty.length).toBe(BAR_WIDTH)
  expect(bar(0, 0)).toEqual(['', '░'.repeat(BAR_WIDTH)])
})

test('percent rounds and pads to four columns', async () => {
  expect(percent(9, 14)).toBe(' 64%')
  expect(percent(0, 0)).toBe('  0%')
})

test('clip cuts long text with an ellipsis', async () => {
  expect(clip('prefiro uma barra na lateral', 10)).toBe('prefiro u…')
  expect(clip('curto', 10)).toBe('curto')
})

import { agentRows, type AgentNode } from './view'

const agent = (id: string, status: string, parentId?: string): AgentNode => ({
  id,
  parentId,
  status,
  type: 'Explore',
  description: id,
})

test('agentRows draws the tree with connectors', async () => {
  const rows = agentRows([
    agent('a', 'running'),
    agent('a1', 'running', 'a'),
    agent('a2', 'waiting', 'a'),
    agent('b', 'idle'),
  ])
  expect(rows.map(r => `${r.prefix}${r.agent.id}`)).toEqual([
    '├─a',
    '│ ├─a1',
    '│ └─a2',
    '└─b',
  ])
})

test('agentRows drops ended agents unless an active one hangs below', async () => {
  const rows = agentRows([
    agent('done', 'completed'),
    agent('parent', 'completed'),
    agent('child', 'running', 'parent'),
    agent('orphan', 'running', 'gone'),
  ])
  expect(rows.map(r => r.agent.id)).toEqual(['parent', 'child', 'orphan'])
})

import { modelTag } from './view'

test('modelTag shortens a model to its family', async () => {
  expect(modelTag('claude-haiku-5-5')).toBe('haiku')
  expect(modelTag('sonnet')).toBe('sonnet')
  expect(modelTag('claude-opus-5-5')).toBe('opus')
  expect(modelTag(undefined)).toBe('?')
})

test('effortLine lists only the used efforts and the default ones', async () => {
  const none = { low: 0, medium: 0, high: 0, xhigh: 0, max: 0 }
  expect(effortLine({ ...none, low: 3, high: 10 }, 2)).toBe('low 3 · high 10 · padrão (high) 2')
  expect(effortLine({ ...none, xhigh: 1 }, 0)).toBe('xhigh 1')
  expect(effortLine(none, 0)).toBe('nenhum ainda')
  expect(effortLine(undefined, undefined)).toBe('nenhum ainda')
})
