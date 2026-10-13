const positiveInt = (value) => {
  const n = Number(value)
  return Number.isInteger(n) && n > 0 ? n : null
}

/**
 * What a thumbs up or down should say about WHERE it was given, so quality can be measured later:
 * the project it was for (a bookmark can be right for one project and wrong for another), the task, the
 * rank the recommendation was shown at, and its match score. The server keeps only a project the user owns.
 */
export const feedbackContext = (selectedContext, recommendations, recommendationId) => {
  const context = selectedContext || {}
  const data = {}

  const projectId = positiveInt(context.type === 'project' ? context.id : context.project_id)
  if (projectId) data.project_id = projectId

  const taskId = positiveInt(context.type === 'task' ? context.id : context.task_id)
  if (taskId) data.task_id = taskId

  const index = (recommendations || []).findIndex((r) => r.id === recommendationId)
  if (index >= 0) {
    data.position = index + 1
    const score = Number(recommendations[index].match_score ?? recommendations[index].score)
    if (Number.isFinite(score)) data.score = score
  }
  return data
}
