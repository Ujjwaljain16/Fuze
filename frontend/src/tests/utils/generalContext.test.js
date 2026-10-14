import { describe, it, expect } from 'vitest'
import { generalRequest, parseInterests } from '../../utils/generalContext'

describe('parseInterests', () => {
  it('splits on commas, semicolons and new lines, trims, and drops blanks and duplicates', () => {
    expect(parseInterests('React , python , system design , backend')).toEqual(['React', 'python', 'system design', 'backend'])
    expect(parseInterests('Go;go\n Rust ,, ')).toEqual(['Go', 'Rust'])
  })

  it('returns nothing for empty or missing input', () => {
    expect(parseInterests('')).toEqual([])
    expect(parseInterests(null)).toEqual([])
    expect(parseInterests(undefined)).toEqual([])
  })
})

describe('generalRequest', () => {
  const interests = ['React', 'python', 'system design']

  it('General asks for all the saved interests together', () => {
    const request = generalRequest('general', interests)
    expect(request.technologies).toBe('React, python, system design')
    expect(request.hasInterests).toBe(true)
    expect(request.description).not.toMatch(/improve my skills/)
  })

  it('Surprise Me picks one interest, and a different random value picks a different one', () => {
    expect(generalRequest('surprise', interests, () => 0).technologies).toBe('React')
    expect(generalRequest('surprise', interests, () => 0.5).technologies).toBe('python')
    expect(generalRequest('surprise', interests, () => 0.99).technologies).toBe('system design')
  })

  it('falls back to the generic wording only when no interests are saved', () => {
    const general = generalRequest('general', [])
    expect(general).toMatchObject({ title: 'General Learning', technologies: '', hasInterests: false })
    expect(generalRequest('surprise', []).hasInterests).toBe(false)
  })
})
