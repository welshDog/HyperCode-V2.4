'use client'

import React from 'react'
import { StudioView } from '@/components/views/StudioView'
import { SkillFinder } from '@/components/views/SkillFinder'
import { CalmCardPanel } from '@/components/crew/CalmCardPanel'
import { useSensory } from '@/components/sensory/SensoryProvider'
import { isCalm } from '@/lib/sensory/settings'

export default function IDEPage(): React.JSX.Element {
  const { settings } = useSensory()

  // Calm layout: the summary comes first and the extra tool is tucked behind one click.
  if (isCalm(settings)) {
    return (
      <>
        <CalmCardPanel />
        <details className="calm-more" data-testid="calm-more">
          <summary>More tools: find a skill</summary>
          <SkillFinder />
        </details>
        <StudioView />
      </>
    )
  }
  return (
    <>
      <SkillFinder />
      <CalmCardPanel />
      <StudioView />
    </>
  )
}
