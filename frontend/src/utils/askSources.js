/** Citations grouped by bookmark: two passages of one page are one source, not two rows. */
export const groupSources = (citations) => {
  const groups = new Map()
  citations.forEach((c) => {
    const key = c.bookmark_id ?? c.url
    if (!groups.has(key)) groups.set(key, { key, title: c.title, url: c.url, passages: [] })
    groups.get(key).passages.push({ n: c.n, snippet: c.snippet })
  })
  return [...groups.values()]
}
