import { describe, it, expect } from 'vitest'
import { feedbackContext } from '../../utils/feedbackContext'

const recs = [
  { id: 11, match_score: 91.5 },
  { id: 12, score: 74 },
  { id: 13 },
]

describe('feedbackContext', () => {
  it('records the project, the rank and the match score of the recommendation', () => {
    expect(feedbackContext({ type: 'project', id: 7 }, recs, 12)).toEqual({ project_id: 7, position: 2, score: 74 })
    expect(feedbackContext({ type: 'project', id: 7 }, recs, 11)).toEqual({ project_id: 7, position: 1, score: 91.5 })
  })

  it('knows the project of a task or subtask, and the task itself', () => {
    expect(feedbackContext({ type: 'task', id: 4, project_id: 7 }, recs, 11)).toEqual({
      project_id: 7, task_id: 4, position: 1, score: 91.5,
    })
    expect(feedbackContext({ type: 'subtask', id: 9, project_id: 7, task_id: 4 }, recs, 13)).toEqual({
      project_id: 7, task_id: 4, position: 3,
    })
  })

  it('sends no project for general or surprise recommendations, and never a bogus id', () => {
    expect(feedbackContext({ type: 'general' }, recs, 11)).toEqual({ position: 1, score: 91.5 })
    expect(feedbackContext({ type: 'project', id: 'abc' }, recs, 11)).toEqual({ position: 1, score: 91.5 })
    expect(feedbackContext({ type: 'project', id: 0 }, recs, 11)).toEqual({ position: 1, score: 91.5 })
    expect(feedbackContext(null, null, 11)).toEqual({})
  })

  it('leaves out the rank of a recommendation that is no longer in the list', () => {
    expect(feedbackContext({ type: 'project', id: 7 }, recs, 999)).toEqual({ project_id: 7 })
  })
})
