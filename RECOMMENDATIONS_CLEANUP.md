# Recommendations Page Cleanup Required

## Issues Found:
1. ❌ Unused state variables (projects, tasks, filter, filterOptions, selectedProject, etc.)
2. ❌ Old fetchProjects() function still present
3. ❌ Old dropdown/filter logic
4. ❌ Duplicate/conflicting useEffects
5. ❌ Unused imports (Select, Filter, etc.)

## Code to Remove:

### State Variables to Delete:
- `projects`
- `tasks`
- `projectsLoading`
- `filter`
- `filterOptions`
- `selectedProject`
- `recommendationForm`
- `showRecommendationForm`
- `taskAnalysis`

### Functions to Delete:
- `fetchProjects()` (entire function)
- Old fetchRecommendations() logic that references selectedProject/filter

### UseEffects to Remove:
- The one that calls fetchProjects()
- The debug logging useEffect

### Imports to Remove:
- `Select` from react-select
- Unused icons: `Filter`, `Plus`, `Settings`, `Search`, `BookOpen`, `Code`, `GraduationCap`, `Briefcase`, `Users`, `Target` (keep TargetIcon)

### UI Sections to Remove:
- Old filter dropdown section
- Old "Selected Project Indicator"
- Old "No Projects Message"

## What to Keep:

### State:
- recommendations
- loading
- refreshing
- emptyMessage
- geminiAvailable
- showContextSelector
- selectedContext
- mousePos
- selectedEngine
- error

### Functions:
- checkGeminiStatus()
- fetchRecommendations() (simplified version without filter/selectedProject)
- handleRefresh()
- handleContextSelect() (NEW)
- handleFeedback()
- handleSaveRecommendation()

### UI:
- Smart Context Selector button
- Selected Context display
- Engine selection
- Gemini status
- Recommendations grid

Starting cleanup now...

