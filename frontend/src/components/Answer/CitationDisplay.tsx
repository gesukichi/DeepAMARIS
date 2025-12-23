import React from 'react'
import { Text, Link } from '@fluentui/react'
import styles from './CitationDisplay.module.css'

interface Citation {
  type: 'web_search' | 'internal_search' | 'error'
  source: string
  title: string
  url?: string
  query?: string
  index?: string
}

interface CitationDisplayProps {
  citations: Citation[]
}

export const CitationDisplay: React.FC<CitationDisplayProps> = ({ citations }) => {
  if (!citations || citations.length === 0) {
    return null
  }

  let webCounter = 0
  let searchCounter = 0

  return (
    <div className={styles.citationsContainer}>
      <Text variant="small" className={styles.citationsHeader}>
        参考情報:
      </Text>
      <ul className={styles.citationsList}>
        {citations.map((citation, index) => {
          if (citation.type === 'web_search') {
            webCounter++
            return (
              <li key={index} className={styles.webCitation}>
                <Text variant="small">
                  [W{webCounter}]{' '}
                  {citation.url ? (
                    <Link href={citation.url} target="_blank">
                      {citation.title}
                    </Link>
                  ) : (
                    citation.title
                  )}
                  <span className={styles.sourceType}>Web検索</span>
                </Text>
              </li>
            )
          } else if (citation.type === 'internal_search') {
            searchCounter++
            return (
              <li key={index} className={styles.internalCitation}>
                <Text variant="small">
                  [S{searchCounter}] {citation.title}
                  <span className={styles.sourceType}>社内文書</span>
                </Text>
              </li>
            )
          } else if (citation.type === 'error') {
            return (
              <li key={index} className={styles.errorCitation}>
                <Text variant="small" className={styles.error}>
                  エラー: {citation.title}
                </Text>
              </li>
            )
          }
          return null
        })}
      </ul>
    </div>
  )
}
