import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  analyzeCompliance,
  DocumentSegment,
} from '../services/geminiService'
import {
  ArrowLeft,
  Upload,
  FileText,
  X,
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronRight,
  Wand2,
  Download,
  Database,
  Save,
  EyeOff,
} from 'lucide-react'
import { fetchWithAuth } from '../api/fetchWithAuth'

type Step = 'UPLOAD' | 'ANALYZING' | 'REPORT'

const NORMS = [
  'Regolamento (UE) 2019/2088 (SFDR)',
  'GDPR (General Data Protection Regulation)',
  'D.lgs. 231/2001',
  'ISO 27001',
  'Normativa Antiriciclaggio (AML)',
  'Database customizzato',
]

const CheckCompliance: React.FC = () => {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('UPLOAD')
  const [selectedNorms, setSelectedNorms] = useState<string[]>([
    'GDPR (General Data Protection Regulation)',
  ])
  const [files, setFiles] = useState<
    { name: string; type: string; data: string }[]
  >([])

  // Stores the full document split into segments
  const [documentSegments, setDocumentSegments] = useState<DocumentSegment[]>(
    []
  )
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(
    null
  )

  // For manual editing
  const [manualEditText, setManualEditText] = useState<string>('')

  const fileInputRef = useRef<HTMLInputElement>(null)
  const segmentRefs = useRef<{ [key: string]: HTMLDivElement | null }>({})

  // --- File Handling ---
  const readFile = (
    file: File
  ): Promise<{ name: string; type: string; data: string }> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        const base64String = (reader.result as string).split(',')[1]
        resolve({ name: file.name, type: file.type, data: base64String })
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]
      try {
        const fileData = await readFile(file)
        setFiles((prev) => [...prev, fileData])
      } catch (err) {
        console.error(err)
      }
    }
  }

  const toggleNorm = (norm: string) => {
    setSelectedNorms((prev) =>
      prev.includes(norm) ? prev.filter((n) => n !== norm) : [...prev, norm]
    )
  }

  const handleStartAnalysis = async () => {
    if (files.length === 0) return
    setStep('ANALYZING')

    const segments = await analyzeCompliance(
      files.map((f) => ({ mimeType: f.type, data: f.data })),
      selectedNorms
    )

    setDocumentSegments(segments)

    // Auto-select first issue if exists
    const firstIssue = segments.find(
      (s) =>
        s.issue &&
        s.issue.status !== 'CORRETTO' &&
        s.issue.status !== 'IGNORATO'
    )
    if (firstIssue) {
      setSelectedSegmentId(firstIssue.id)
      setManualEditText(firstIssue.text)
    }

    setStep('REPORT')
  }

  // --- Corrections & Navigation ---

  const handleSelectSegment = (segment: DocumentSegment) => {
    setSelectedSegmentId(segment.id)
    setManualEditText(segment.text)
    const element = segmentRefs.current[segment.id]
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  const handleApplyCorrection = (segmentId: string) => {
    setDocumentSegments((prev) =>
      prev.map((seg) => {
        if (seg.id === segmentId && seg.issue) {
          return {
            ...seg,
            text: seg.issue.suggestion, // Replace text with AI suggestion
            issue: {
              ...seg.issue,
              status: 'CORRETTO',
            },
          }
        }
        return seg
      })
    )
  }

  const handleIgnoreCorrection = (segmentId: string) => {
    setDocumentSegments((prev) =>
      prev.map((seg) => {
        if (seg.id === segmentId && seg.issue) {
          // We keep the issue structure but mark it as ignored/conforme so it stops showing as an error
          return {
            ...seg,
            issue: {
              ...seg.issue,
              status: 'IGNORATO', // Custom status for ignored issues
            },
          }
        }
        return seg
      })
    )
  }

  const handleSaveManualEdit = (segmentId: string) => {
    setDocumentSegments((prev) =>
      prev.map((seg) => {
        if (seg.id === segmentId) {
          return {
            ...seg,
            text: manualEditText,
            issue: seg.issue ? { ...seg.issue, status: 'CORRETTO' } : undefined,
          }
        }
        return seg
      })
    )
  }

  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false)
  const [downloadLoading, setDownloadLoading] = useState(false)

  const handleDownloadChoice = async (format: 'pdf' | 'word') => {
    // Request backend to generate the chosen format and download the returned URL
    const fullText = documentSegments.map((s) => s.text).join('\n\n')
    const payload = {
      tipo_documento: 'ComplianceReport',
      titolo: 'Report Conformità',
      contenuto: fullText,
      note: '',
    }

    try {
      setDownloadLoading(true)
      const res = await fetchWithAuth('/openai/draft/export/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res || !res.ok) {
        console.error('Export failed', res && res.status)
        setDownloadLoading(false)
        setDownloadMenuOpen(false)
        return
      }
      const json = await res.json()
      const urls = json.urls || {}
      const fileUrl = format === 'pdf' ? urls.pdf : urls.word
      if (!fileUrl) {
        console.error('No file url returned for', format)
        setDownloadLoading(false)
        setDownloadMenuOpen(false)
        return
      }

      // Trigger download
      const a = document.createElement('a')
      a.href = fileUrl
      a.download = `Report_Conformita_${new Date().toISOString().slice(0, 10)}.${format === 'pdf' ? 'pdf' : 'docx'}`
      a.target = '_blank'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (err) {
      console.error('Error exporting report', err)
    } finally {
      setDownloadLoading(false)
      setDownloadMenuOpen(false)
    }
  }

  // --- UI Helpers ---

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'NON_CONFORME':
        return 'text-red-700 bg-red-50 border-red-200'
      case 'BORDERLINE':
        return 'text-amber-700 bg-amber-50 border-amber-200'
      case 'CONFORME':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200'
      case 'CORRETTO':
        return 'text-blue-700 bg-blue-50 border-blue-200'
      case 'IGNORATO':
        return 'text-gray-500 bg-gray-50 border-gray-200'
      default:
        return 'text-slate-600 bg-slate-50 border-slate-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'NON_CONFORME':
        return <AlertCircle className="w-4 h-4" />
      case 'BORDERLINE':
        return <AlertTriangle className="w-4 h-4" />
      case 'CORRETTO':
        return <CheckCircle className="w-4 h-4" />
      case 'CONFORME':
        return <ShieldCheck className="w-4 h-4" />
      case 'IGNORATO':
        return <EyeOff className="w-4 h-4" />
      default:
        return <ShieldCheck className="w-4 h-4" />
    }
  }

  // --- RENDERERS ---

  if (step === 'ANALYZING') {
    return (
      <div className="h-[calc(100vh-4rem)] flex flex-col items-center justify-center bg-[#F8FAFC]">
        <Loader2 className="w-16 h-16 text-slate-900 animate-spin mb-6" />
        <h3 className="text-2xl text-slate-900 mb-2 text-center">
          Analisi in corso...
        </h3>
        <p className="text-slate-500 text-lg text-center">
          Analizzando l'intero documento.
        </p>
      </div>
    )
  }

  if (step === 'REPORT') {
    const activeIssues = documentSegments.filter(
      (s) =>
        s.issue &&
        s.issue.status !== 'CORRETTO' &&
        s.issue.status !== 'IGNORATO' &&
        s.issue.status !== 'CONFORME'
    )
    const issuesCount = activeIssues.length
    const fixedCount = documentSegments.filter(
      (s) =>
        s.issue &&
        (s.issue.status === 'CORRETTO' || s.issue.status === 'IGNORATO')
    ).length

    return (
      <div className="h-[calc(100vh)] flex flex-col bg-[#F8FAFC] overflow-auto">
        {/* Report Header */}
        <div className="px-8 py-4 bg-white border-b border-slate-300 flex justify-between items-center shadow-sm z-10 relative">
          <div>
            <div className="flex items-center gap-3 mb-1 relative">
              <button
                onClick={() => setStep('UPLOAD')}
                className="p-1 hover:bg-slate-100 rounded-full transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-slate-400" />
              </button>
              <h2 className="text-1xl font-bold text-slate-900 absolute left-9">
                Report di Conformità
              </h2>
            </div>
            <div className="flex items-center gap-4 ml-9">
              <span className="text-slate-500 text-sm">{files[0]?.name}</span>
              <div className="h-4 w-px bg-slate-300"></div>
              <span className="text-slate-500 text-sm flex items-center">
                <ShieldCheck className="w-4 h-4 mr-1 text-[#C5A572]" />
                {documentSegments.filter((s) => s.issue).length} Punti rilevati
              </span>
            </div>
          </div>
          <div className="flex gap-4 relative">
            <div className="relative">
              <button
                onClick={() => setDownloadMenuOpen((open) => !open)}
                className="bg-[#172554] text-white px-6 py-2 rounded-sm hover:bg-[#172569] transition-all flex items-center font-medium shadow-md text-sm"
              >
                {downloadLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Download className="w-4 h-4 mr-2 text-[#C5A572]" />
                )}
                SCARICA REPORT CORRETTO
              </button>

              {downloadMenuOpen && (
                <div className="absolute right-0 mt-2 w-40 bg-white border border-slate-200 rounded shadow-lg z-50">
                  <button
                    onClick={() => {
                      handleDownloadChoice('pdf')
                      setDownloadMenuOpen(false)
                    }}
                    className="w-full text-left text-sm px-4 py-2 hover:bg-slate-50"
                  >
                    Scarica PDF
                  </button>
                  <button
                    onClick={() => {
                      handleDownloadChoice('word')
                      setDownloadMenuOpen(false)
                    }}
                    className="w-full text-left text-sm px-4 py-2 hover:bg-slate-50"
                  >
                    Scarica Word
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Split View */}
        <div className="flex-1 flex min-h-0 overflow-y-auto">
          {/* Left: Issues Navigation List */}
          <div className="w-[400px] bg-white border-r border-slate-300 flex flex-col flex-shrink-0">
            <div className="p-6 border-b border-slate-200">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                Riepilogo Criticità
              </h3>
              <p className="text-slate-400 text-sm">
                {issuesCount} da risolvere, {fixedCount} gestite
              </p>
            </div>

            <div className="p-4 space-y-3">
              {documentSegments
                .filter((s) => s.issue)
                .map((seg) => (
                  <div
                    key={seg.id}
                    onClick={() => handleSelectSegment(seg)}
                    className={`p-4 rounded-sm border cursor-pointer transition-all ${
                      selectedSegmentId === seg.id
                        ? 'border-slate-900 bg-slate-50 ring-1 ring-slate-900 shadow-md transform scale-[1.02]'
                        : 'border-slate-200 bg-white hover:border-slate-400'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div
                        className={`flex items-center px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wide ${getStatusColor(seg.issue!.status)}`}
                      >
                        {getStatusIcon(seg.issue!.status)}
                        <span className="ml-1.5">
                          {seg.issue!.status.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                    <h4 className="font-bold text-base text-slate-900 mb-1 leading-snug">
                      {seg.issue!.title}
                    </h4>
                    <p className="text-xs text-slate-500 line-clamp-2">
                      {seg.issue!.description}
                    </p>
                  </div>
                ))}

              {documentSegments.filter((s) => s.issue).length === 0 && (
                <div className="text-center py-10 text-slate-400 px-4">
                  <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-200" />
                  <p>
                    Il documento sembra pienamente conforme alle normative
                    selezionate.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right: Full Document Viewer */}
          <div className="flex-1 bg-slate-100 p-8 min-h-0">
            <div className="max-w-4xl mx-auto bg-white shadow-lg p-12 border border-slate-200">
              {documentSegments.map((seg) => (
                <div
                  key={seg.id}
                  ref={(el) => {
                    segmentRefs.current[seg.id] = el
                  }}
                  className={`mb-6 relative transition-all duration-500 rounded-md ${
                    selectedSegmentId === seg.id ? 'z-10' : ''
                  }`}
                >
                  {/* TEXT DISPLAY LOGIC */}
                  {selectedSegmentId === seg.id &&
                  seg.issue &&
                  seg.issue.status !== 'CORRETTO' &&
                  seg.issue.status !== 'IGNORATO' ? (
                    <div className="relative">
                      <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                        Modifica Manuale (Testo Originale)
                      </label>
                      <textarea
                        value={manualEditText}
                        onChange={(e) => setManualEditText(e.target.value)}
                        className="w-full p-4 border-2 border-slate-400 rounded-md text-lg leading-relaxed focus:outline-none focus:border-[#1E3A8A] bg-white shadow-inner"
                        rows={Math.max(
                          4,
                          Math.ceil(manualEditText.length / 80)
                        )}
                      />
                      <div className="flex justify-end mt-2">
                        <button
                          onClick={() => handleSaveManualEdit(seg.id)}
                          className="flex items-center text-xs font-bold text-slate-600 hover:text-slate-900 uppercase tracking-wide bg-slate-200 px-3 py-1 rounded"
                        >
                          <Save className="w-3 h-3 mr-1" />
                          Salva Modifica
                        </button>
                      </div>
                    </div>
                  ) : (
                    // READ ONLY MODE
                    <p
                      className={`text-lg leading-relaxed text-slate-800 p-4 rounded transition-colors border border-transparent ${
                        selectedSegmentId === seg.id
                          ? 'bg-blue-50/50 border-blue-200'
                          : seg.issue &&
                              seg.issue.status !== 'CORRETTO' &&
                              seg.issue.status !== 'IGNORATO'
                            ? 'bg-rose-50/30'
                            : ''
                      } ${seg.issue && seg.issue.status === 'CORRETTO' ? 'text-emerald-900 bg-emerald-50/30' : ''} ${seg.issue && seg.issue.status === 'IGNORATO' ? 'text-slate-500 bg-gray-50' : ''}`}
                    >
                      {seg.text}
                    </p>
                  )}

                  {/* Inline Action Box (Only if selected and has issue AND not resolved) */}
                  {selectedSegmentId === seg.id &&
                    seg.issue &&
                    seg.issue.status !== 'CORRETTO' &&
                    seg.issue.status !== 'IGNORATO' && (
                      <div className="mt-4 ml-4 bg-white border border-slate-300 rounded-sm shadow-xl p-6 animate-in fade-in slide-in-from-top-2 relative border-l-4 border-l-rose-500">
                        <div className="absolute -top-3 left-8 w-4 h-4 bg-white border-t border-l border-slate-300 transform rotate-45"></div>

                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h5 className="text-sm font-bold text-rose-700 uppercase tracking-wide flex items-center">
                              <AlertTriangle className="w-4 h-4 mr-2" />
                              Rilevata Criticità: {seg.issue.title}
                            </h5>
                            <p className="text-xs text-slate-500 mt-1">
                              Normativa: {seg.issue.referenceNorm}
                            </p>
                          </div>
                        </div>

                        <p className="text-slate-600 text-sm mb-4 bg-slate-50 p-3 rounded border border-slate-100">
                          {seg.issue.description}
                        </p>

                        <div className="border-t border-slate-100 pt-4">
                          <p className="text-xs font-bold text-slate-400 uppercase mb-2 flex items-center">
                            <Wand2 className="w-3 h-3 mr-1" />
                            Suggerimento Correttivo AI
                          </p>
                          <div className="text-base font-medium text-slate-800 mb-4 p-3 bg-emerald-50 border border-emerald-100 rounded text-emerald-900">
                            "{seg.issue.suggestion}"
                          </div>

                          <div className="flex gap-3">
                            <button
                              onClick={() => handleApplyCorrection(seg.id)}
                              className="bg-[#1E3A8A] text-white px-4 py-2 rounded-sm text-sm font-medium hover:bg-blue-900 transition-colors shadow-sm flex items-center"
                            >
                              <CheckCircle className="w-4 h-4 mr-2" />
                              Applica Correzione
                            </button>
                            <button
                              onClick={() => handleIgnoreCorrection(seg.id)}
                              className="text-slate-500 px-4 py-2 rounded-sm text-sm font-medium hover:bg-slate-100 transition-colors flex items-center"
                            >
                              <EyeOff className="w-4 h-4 mr-2" />
                              Ignora
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // DEFAULT: UPLOAD STEP
  return (
    <div className="w-full h-[calc(100vh-4rem)] p-8 flex items-start justify-center">
      <div className="max-w-6xl w-full flex flex-col gap-8">
        {/* Header */}
        <div className="flex items-left justify-left">
          <div className="text-left">
            <button
              onClick={() => navigate('/')}
              className="mr-4 p-2 hover:bg-slate-200 rounded-full transition-colors lg:hidden"
            >
              <ArrowLeft className="w-5 h-5 text-slate-600" />
            </button>
            <div>
              <h2 className="text-1xl font-bold text-slate-900">
                Check Compliance
              </h2>
              <p className="text-slate-500 font-light text-sm">
                Analisi automatica di conformità normativa
              </p>
            </div>
          </div>
        </div>

        {/* Configuration Card */}
        <div className="bg-white rounded-sm border border-slate-300 p-8 shadow-sm w-full">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-6 flex items-center">
            <ShieldCheck className="w-5 h-5 mr-2 text-[#C5A572]" />
            Seleziona Database Normativi
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {NORMS.map((norm) => (
              <label
                key={norm}
                className={`flex items-center p-4 rounded-md border cursor-pointer transition-all ${
                  selectedNorms.includes(norm)
                    ? 'border-[#1E3A8A] bg-blue-50 ring-1 ring-[#1E3A8A]'
                    : 'border-slate-200 hover:border-slate-400 bg-white'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded border flex items-center justify-center mr-3 transition-colors ${
                    selectedNorms.includes(norm)
                      ? 'bg-[#1E3A8A] border-[#1E3A8A]'
                      : 'border-slate-300 bg-white'
                  }`}
                >
                  {selectedNorms.includes(norm) && (
                    <CheckCircle className="w-3.5 h-3.5 text-white" />
                  )}
                </div>
                <span
                  className={`text-sm font-medium ${selectedNorms.includes(norm) ? 'text-[#1E3A8A]' : 'text-slate-700'}`}
                >
                  {norm}
                </span>
                {norm === 'Database customizzato' && (
                  <Database
                    className={`w-4 h-4 ml-auto ${selectedNorms.includes(norm) ? 'text-[#1E3A8A]' : 'text-slate-400'}`}
                  />
                )}
                <input
                  type="checkbox"
                  className="hidden"
                  checked={selectedNorms.includes(norm)}
                  onChange={() => toggleNorm(norm)}
                />
              </label>
            ))}
          </div>
        </div>

        {/* Upload Area */}
        <div className="bg-white rounded-sm border border-slate-300 p-8 shadow-sm flex-1 flex flex-col w-full min-h-0 mb-10">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-6 flex items-center">
            <Upload className="w-5 h-5 mr-2 text-[#C5A572]" />
            Carica Documenti
          </h3>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="flex-1 border-2 border-dashed border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors flex flex-col items-center justify-center cursor-pointer min-h-[300px]"
          >
            <div className="bg-white p-4 rounded-full shadow-sm mb-4">
              <Upload className="w-10 h-10 text-[#1E3A8A]" />
            </div>
            <h4 className="text-xl font-medium text-slate-900 mb-2">
              Carica o trascina il tuo file qui
            </h4>
            <p className="text-slate-500 font-light text-sm">
              Accettati solo PDF e Word (.doc, .docx).
            </p>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileChange}
              accept=".pdf,.doc,.docx,.txt"
            />
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mt-8">
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-xs font-semibold text-slate-700">
                  FILE SELEZIONATI ({files.length})
                </h4>
                <button
                  onClick={() => setFiles([])}
                  className="text-xs text-red-500 hover:text-red-700 font-medium"
                >
                  Rimuovi tutti
                </button>
              </div>
              <div className="space-y-3">
                {files.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-4 bg-white border border-slate-200 rounded-md"
                  >
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-blue-50 text-[#1E3A8A] rounded flex items-center justify-center mr-4">
                        <FileText className="w-6 h-6" />
                      </div>
                      <div>
                        <p className="text-sm text-slate-900">
                          {file.name}
                        </p>
                        <p className="text-xs text-slate-400 uppercase">
                          {file.type.split('/')[1] || 'DOC'}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() =>
                        setFiles(files.filter((_, i) => i !== idx))
                      }
                    >
                      <X className="w-5 h-5 text-slate-300 hover:text-slate-500" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Button */}
          <div className="mt-8 flex justify-center">
            <button
              onClick={handleStartAnalysis}
              disabled={files.length === 0}
              className="bg-[#1E3A8A] text-white px-8 py-4 rounded-md text-sm text-base shadow-lg hover:bg-blue-900 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              AVVIA ANALISI
              <ChevronRight className="w-5 h-5 ml-2" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CheckCompliance;