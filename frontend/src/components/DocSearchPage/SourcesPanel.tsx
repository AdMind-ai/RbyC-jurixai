import { useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink, FileText } from 'lucide-react'

export interface SourceItem {
  id: string
  title: string
  url: string
  type?: string
}

export default function SourcesPanel({ sources }: { sources: SourceItem[] }) {
  const [areSourcesOpen, setAreSourcesOpen] = useState(false)

  const getFileIcon = (type?: string) => {
    // Always use the same icon, vary only the color by file type
    const t = (type || '').toLowerCase()
    let colorClass = 'text-slate-600'
    if (t === 'pdf') colorClass = 'text-red-600'
    else if (t === 'doc' || t === 'docx') colorClass = 'text-blue-600'
    else if (t === 'xls' || t === 'xlsx' || t === 'csv') colorClass = 'text-emerald-600'
    else if (t === 'ppt' || t === 'pptx') colorClass = 'text-orange-600'

    return <FileText className={`w-6 h-6 ${colorClass}`} />
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm mt-6">
      <div
        onClick={() => setAreSourcesOpen(!areSourcesOpen)}
        className="flex items-center justify-between px-6 py-5 bg-slate-50 border-b border-slate-100 cursor-pointer hover:bg-slate-100 transition-colors"
      >
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-slate-500 uppercase tracking-wider">Fonti e Riferimenti</span>
          <span className="bg-blue-100 text-blue-800 text-sm font-bold px-3 py-1 rounded-full">
            {sources.length} trovati
          </span>
        </div>
        {areSourcesOpen ? (
          <ChevronUp className="w-3 h-3 text-slate-400" />
        ) : (
          <ChevronDown className="w-3 h-3 text-slate-400" />
        )}
      </div>

      {areSourcesOpen && (
        <div className="p-6 bg-slate-50/50 grid grid-cols-1 md:grid-cols-2 gap-6">
          {sources.map((source) => (
            <a
              key={source.id}
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-lg hover:border-blue-200 transition-all group cursor-pointer flex items-center justify-between"
            >
              <div className="flex items-center gap-5 overflow-hidden">
                <div className="bg-slate-50 p-3 rounded-lg flex-shrink-0 group-hover:bg-slate-100 transition-colors">
                  {getFileIcon(source.type)}
                </div>
                <div className="flex flex-col overflow-hidden">
                  <span className="font-bold text-slate-900 text-sm" title={source.title}>
                    {source.title}
                  </span>
                </div>
              </div>

              <ExternalLink className="w-6 h-6 text-slate-300 group-hover:text-[#1E3A8A] transition-colors flex-shrink-0 ml-4" />
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
