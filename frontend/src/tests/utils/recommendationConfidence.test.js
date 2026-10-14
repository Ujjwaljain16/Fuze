import { describe, it, expect } from 'vitest'
import { splitByConfidence } from '../../utils/recommendationConfidence'

const rec = (id, weak) => (weak === undefined ? { id } : { id, weak_match: weak })

describe('splitByConfidence', () => {
  it('folds weak matches away when something stronger is shown, keeping the order', () => {
    const list = [rec(1, false), rec(2, true), rec(3, false), rec(4, true)]
    const result = splitByConfidence(list, false)
    expect(result.visible.map((r) => r.id)).toEqual([1, 3])
    expect(result.weakCount).toBe(2)
    expect(result.folded).toBe(true)
  })

  it('shows everything, in the original order, once expanded', () => {
    const list = [rec(1, false), rec(2, true), rec(3, false)]
    const result = splitByConfidence(list, true)
    expect(result.visible.map((r) => r.id)).toEqual([1, 2, 3])
    expect(result.weakCount).toBe(1)           // the toggle stays, to fold them again
    expect(result.folded).toBe(false)
  })

  it('never hides everything: with nothing strong all results stay visible and there is no toggle', () => {
    const list = [rec(1, true), rec(2, true)]
    const result = splitByConfidence(list, false)
    expect(result.visible).toHaveLength(2)
    expect(result.weakCount).toBe(0)
  })

  it('treats a missing flag as unknown, not weak', () => {
    const list = [rec(1), rec(2, undefined), rec(3, false)]
    const result = splitByConfidence(list, false)
    expect(result.visible).toHaveLength(3)
    expect(result.weakCount).toBe(0)
  })

  it('handles an empty list', () => {
    expect(splitByConfidence([], false)).toEqual({ visible: [], weakCount: 0, folded: false })
  })
})
