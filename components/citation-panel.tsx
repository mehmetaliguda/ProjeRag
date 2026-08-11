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
    <>
      {/* Arka plan overlay - tıklayınca da kapansın */}
      <div
        onClick={handleClose}
        className={`fixed inset-0 z-40 bg-black/20 transition-opacity duration-300 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
      />

      <div
        className={`fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-gray-200 bg-white shadow-xl transition-transform duration-300 ease-in-out sm:w-[420px] ${
          isVisible ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex flex-shrink-0 items-center gap-2.5 border-b border-gray-100 px-4 py-3">
          <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-700">
            {activeCitation.page}
          </span>

          <div className="min-w-0 flex-1">
            <h3 className="truncate text-sm font-semibold text-gray-800">Sayfa {activeCitation.page}</h3>
            <p className="text-xs text-gray-400">Kaynak belge</p>
          </div>

          {activeCitation.pdf_url && (
            <a
              href={activeCitation.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Yeni sekmede aç"
              className="flex-shrink-0 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-blue-600"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
          )}

          <button
            onClick={handleClose}
            aria-label="Kapat"
            className="flex-shrink-0 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
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

          <div className="p-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
              Alıntılanan metin
            </p>
            <div className="rounded-lg bg-amber-50 px-3.5 py-3 text-sm leading-relaxed text-gray-800 ring-1 ring-inset ring-amber-100">
              {activeCitation.text}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}