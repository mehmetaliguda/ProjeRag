'use client'

import { Fragment, type ReactNode } from 'react'
import { useAppStore } from '@/lib/store'
import type { Message } from '@/lib/store'

interface ChatMessageProps {
  message: Message
}

const CITATION_PATTERN = /\[\[c:([\d,]+)\]\]/g

export function ChatMessage({ message }: ChatMessageProps) {
  // 🔥 DEBUG İÇİN EKLE
  console.log('🔍 ChatMessage: Message content:', message.content);
  console.log('🔍 ChatMessage: Message citations:', message.citations);
  console.log('🔍 ChatMessage: Message role:', message.role);
  console.log('🔍 ChatMessage: Message ID:', message.id);
  
  const setActiveCitation = useAppStore((state) => state.setActiveCitation)

  const renderContentWithCitations = (text: string): ReactNode[] => {
    // 🔥 DEBUG İÇİN EKLE
    console.log('🔍 renderContentWithCitations called with text length:', text?.length);
    console.log('🔍 renderContentWithCitations text preview:', text?.substring(0, 100) + '...');
    
    if (!text || typeof text !== 'string') {
      console.log('❌ Text is empty or not a string');
      return [<span key="empty">Metin bulunamadı</span>]
    }

    const nodes: ReactNode[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null
    let matchCount = 0

    CITATION_PATTERN.lastIndex = 0
    let foundMatches = 0
    
    while ((match = CITATION_PATTERN.exec(text)) !== null) {
      foundMatches++
      const [fullMatch, idsRaw] = match
      const matchStart = match.index
      const matchEnd = matchStart + fullMatch.length

      console.log(`🔍 Found citation ${foundMatches}:`, {
        fullMatch,
        idsRaw,
        matchStart,
        matchEnd
      });

      if (matchStart > lastIndex) {
        const textChunk = text.slice(lastIndex, matchStart)
        console.log(`📝 Text chunk before citation ${foundMatches}:`, textChunk);
        nodes.push(
          <Fragment key={`text-${lastIndex}`}>{textChunk}</Fragment>
        )
      }

      const ids = idsRaw.split(',').map((id) => id.trim()).filter(Boolean)
      console.log(`🔍 Citation ${foundMatches} IDs:`, ids);

      ids.forEach((id) => {
        const citation = message.citations?.[id]
        matchCount += 1
        
        console.log(`🔍 Processing citation ID ${id}:`, {
          found: !!citation,
          citation: citation,
          availableCitations: Object.keys(message.citations || {})
        });

        if (!citation) {
          // Citation not found — leave as plain text, fail silently.
          console.log(`⚠️ Citation ${id} not found in message.citations`);
          nodes.push(<Fragment key={`missing-${matchStart}-${id}`}>{`[${id}]`}</Fragment>)
          return
        }
        
        console.log(`✅ Citation ${id} found, creating button`);
        nodes.push(
          <button
            key={`citation-${matchStart}-${id}-${matchCount}`}
            onClick={() => {
              console.log(`🖱️ Citation button ${id} clicked, setting active citation:`, citation);
              setActiveCitation(citation)
            }}
            className="mx-0.5 text-xs font-medium text-blue-600 underline underline-offset-2 hover:text-blue-800"
          >
            [{id}]
          </button>
        )
      })

      lastIndex = matchEnd
    }

    console.log(`🔍 Total citations found: ${foundMatches}`);

    if (lastIndex < text.length) {
      const remainingText = text.slice(lastIndex)
      console.log(`📝 Remaining text after citations:`, remainingText);
      nodes.push(<Fragment key={`text-${lastIndex}-end`}>{remainingText}</Fragment>)
    }

    console.log(`✅ Rendered ${nodes.length} nodes`);
    return nodes
  }

  return (
    <div
      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
          message.role === 'user'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <span className="whitespace-pre-wrap">
          {renderContentWithCitations(message.content)}
        </span>
      </div>
    </div>
  )
}