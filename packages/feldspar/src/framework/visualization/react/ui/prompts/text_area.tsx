import React, { JSX, useEffect } from 'react'
import { Weak } from '../../../../helpers'
import { PropsUIPromptTextArea } from '../../../../types/prompts'
import { PromptContext } from './factory'

type Props = Weak<PropsUIPromptTextArea> & PromptContext

export const TextArea = (props: Props): JSX.Element => {
  const { id, initialValue, rows, onDataSubmissionDataChanged } = props
  const [value, setValue] = React.useState(initialValue ?? '')

  // Register initial value so it is captured even if the user never edits
  useEffect(() => {
    onDataSubmissionDataChanged?.(id ?? '', initialValue ?? '')
  }, [])

  function handleChange (e: React.ChangeEvent<HTMLTextAreaElement>): void {
    const next = e.target.value
    setValue(next)
    onDataSubmissionDataChanged?.(id ?? '', next)
  }

  return (
    <textarea
      className='w-full font-mono text-sm border border-grey3 rounded p-3 my-2 resize-y focus:outline-none focus:border-primary'
      rows={rows ?? 8}
      value={value}
      onChange={handleChange}
    />
  )
}
