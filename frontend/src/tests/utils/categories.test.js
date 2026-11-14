import { describe, it, expect } from 'vitest'
import { CATEGORIES, FILTER_CATEGORIES } from '../../utils/categories'

describe('bookmark categories', () => {
  it('lets the library filter offer every category the save form can store', () => {
    const filterValues = FILTER_CATEGORIES.map((c) => c.value)
    for (const { value } of CATEGORIES) expect(filterValues).toContain(value)
    expect(filterValues[0]).toBe('all')
  })

  it('has unique lowercase values, because the server compares them exactly', () => {
    const values = CATEGORIES.map((c) => c.value)
    expect(new Set(values).size).toBe(values.length)
    for (const v of values) expect(v).toBe(v.toLowerCase())
    expect(values).toContain('other')
  })
})
