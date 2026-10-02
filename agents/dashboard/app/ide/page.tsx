'use client'

import React from 'react'
import { StudioView } from '@/components/views/StudioView'
import { SkillFinder } from '@/components/views/SkillFinder'
import { CalmCardPanel } from '@/components/crew/CalmCardPanel'

export default function IDEPage(): React.JSX.Element {
  return (
    <>
      <SkillFinder />
      <CalmCardPanel />
      <StudioView />
    </>
  )
}
