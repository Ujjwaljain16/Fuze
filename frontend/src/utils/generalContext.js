/**
 * What the "General" and "Surprise Me" choices ask the recommender for. They used to send a fixed sentence
 * ("General Learning: I want to learn and improve my skills"), so the engine returned the user's bookmarks
 * about learning resources and roadmaps. They now use the technology interests saved on the profile.
 */

/** "React , python;system design\nbackend" -> ['React', 'python', 'system design', 'backend'] (no duplicates). */
export const parseInterests = (raw) => {
  const seen = new Set()
  const out = []
  for (const part of String(raw || '').split(/[,;\n]/)) {
    const item = part.trim()
    if (item && !seen.has(item.toLowerCase())) {
      seen.add(item.toLowerCase())
      out.push(item)
    }
  }
  return out
}

/**
 * kind: 'general' (all interests together) or 'surprise' (one interest picked at random, so each press differs).
 * With no saved interests the old wording is used, since there is nothing better to ask for.
 */
export const generalRequest = (kind, interests, random = Math.random) => {
  const list = interests || []
  if (list.length === 0) {
    return kind === 'surprise'
      ? { title: 'Surprise Me', description: 'Random quality learning content', technologies: '', hasInterests: false }
      : { title: 'General Learning', description: 'I want to learn and improve my skills', technologies: '', hasInterests: false }
  }
  if (kind === 'surprise') {
    const pick = list[Math.floor(random() * list.length)]
    return { title: 'Surprise Me', description: 'Something worth reading about', technologies: pick, hasInterests: true }
  }
  return {
    title: 'General',
    description: 'Things I want to learn and build with',
    technologies: list.join(', '),
    hasInterests: true,
  }
}
