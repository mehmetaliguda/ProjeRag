'use client'

import { useEffect, useState } from 'react'
import { useAppStore } from '@/lib/store'

export function CitationPanel() {
  const activeCitation = useAppStore((state) => state.activeCitation)
  const setActiveCitation = useAppStore((state) => state.setActiveCitation)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (activeCitation) {
      // Mount first, then animate in on next tick.
      const id = requestAnimationFrame(() => setIsVisible(true))
      return () => cancelAnimationFrame(id)
    }
    setIsVisible(false)
  }, [activeCitation])

  if (!activeCitation) return null

  const handleClose = () => setActiveCitation(null)

  return (
    <div
      className={`fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-gray-200 bg-white shadow-xl transition-transform duration-300 ease-in-out sm:w-[420px] ${
        isVisible ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      <div className="flex flex-shrink-0 items-center justify-between border-b border-gray-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-800">Sayfa {activeCitation.page}</h3>
        <button
          onClick={handleClose}
          aria-label="Kapat"
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeCitation.pdf_url ? (
          <iframe
            src={activeCitation.pdf_url}
            title={`Kaynak sayfa ${activeCitation.page}`}
            className="h-72 w-full border-b border-gray-100"
          />
        ) : (
          <div className="flex h-40 items-center justify-center border-b border-gray-100 px-4 text-center text-sm text-gray-400">
            PDF önizlemesi bu kaynak için mevcut değil
          </div>
        )}

        {activeCitation.image && (
          <div className="border-b border-gray-100 p-4">
            <img
              src={activeCitation.image}
              alt={`Kaynak önizlemesi — sayfa ${activeCitation.page}`}
              className="w-full rounded-md object-contain"
            />
          </div>
        )}

        <div className="p-4">
          <blockquote className="border-l-2 border-blue-300 pl-3 text-sm italic leading-relaxed text-gray-700">
            {activeCitation.text}
          </blockquote>
        </div>
      </div>
    </div>
  )
}
