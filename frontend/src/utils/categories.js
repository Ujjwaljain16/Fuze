// One list of bookmark categories, used by the save form and the library filter. They used to be two different
// lists (the filter offered Work/Personal/Entertainment, which the save form never stored), so most saved
// categories could not be filtered.
export const CATEGORIES = [
  { value: 'other', label: 'Other' },
  { value: 'technology', label: 'Technology' },
  { value: 'programming', label: 'Programming' },
  { value: 'design', label: 'Design' },
  { value: 'business', label: 'Business' },
  { value: 'education', label: 'Education' },
  { value: 'news', label: 'News' },
  { value: 'tutorial', label: 'Tutorial' },
  { value: 'research', label: 'Research' },
]

export const FILTER_CATEGORIES = [{ value: 'all', label: 'All Categories' }, ...CATEGORIES]
