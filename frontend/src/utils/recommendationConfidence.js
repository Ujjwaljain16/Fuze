/**
 * Weak matches are the ones the engine's cross-encoder check does not tie to the current context
 * (`weak_match: true`). They are folded away when there is something stronger to show; with nothing
 * strong, or no check result at all (the field is absent), every recommendation stays visible.
 */
export function splitByConfidence(recommendations, showWeak) {
  const weakCount = recommendations.filter((rec) => rec.weak_match === true).length
  const hasStrong = recommendations.length - weakCount > 0
  const foldable = hasStrong && weakCount > 0
  const fold = foldable && !showWeak
  return {
    visible: fold ? recommendations.filter((rec) => rec.weak_match !== true) : recommendations,
    weakCount: foldable ? weakCount : 0,   // how many can be folded: drives the toggle
    folded: fold,
  }
}
