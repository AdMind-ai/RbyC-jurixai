import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload,
  FileText,
  Plus,
  X,
  Trash,
  Sparkles,
  Building2,
  Check,
  Loader2,
  ArrowLeft,
  FileDown,
} from 'lucide-react'
import { fetchWithAuth } from '../api/fetchWithAuth'
import '@react-pdf-viewer/core/lib/styles/index.css'
import '@react-pdf-viewer/zoom/lib/styles/index.css'
import { Worker, Viewer } from '@react-pdf-viewer/core'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.js?url'

interface Company {
  id: string
  name: string
  documentTitle?: string
  letterheadName?: string
}

type Tab = 'GENERATE' | 'ADD_COMPANY'

export const DraftDocument: React.FC = () => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('GENERATE')

  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('')
  const [docType, setDocType] = useState<string>('')
  const [instructions, setInstructions] = useState<string>('')
  const [contextFiles, setContextFiles] = useState<
    { name: string; type: string; data: string }[]
  >([])
  const [loading, setLoading] = useState(false)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [wordUrl, setWordUrl] = useState<string | null>(null)
  // If the PDF server (SAS blob) blocks embedding via CORS, we fetch the PDF
  // as ArrayBuffer and pass a Uint8Array to the Viewer as a fallback.
  const [pdfData, setPdfData] = useState<Uint8Array | null>(null)
  const [pdfFetchError, setPdfFetchError] = useState<string | null>(null)

  const [companies, setCompanies] = useState<Company[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newCompanyName, setNewCompanyName] = useState('')
  const [newCompanyFile, setNewCompanyFile] = useState<string | null>(null)
  const [newCompanyFileData, setNewCompanyFileData] = useState<string | null>(
    null
  )
  const [newCompanyFileMime, setNewCompanyFileMime] = useState<string | null>(
    null
  )
  const [newCompanyDocumentTitle, setNewCompanyDocumentTitle] = useState('')
  const [newCompanyWordFile, setNewCompanyWordFile] = useState<string | null>(
    null
  )
  const [newCompanyWordFileData, setNewCompanyWordFileData] = useState<
    string | null
  >(null)
  const [newCompanyWordFileMime, setNewCompanyWordFileMime] = useState<
    string | null
  >(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const companyFileRef = useRef<HTMLInputElement>(null)
  const companyWordFileRef = useRef<HTMLInputElement>(null)

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

  const fetchCompanies = async () => {
    try {
      const res = await fetchWithAuth('/company/document-layout/')
      if (res.ok) {
        const data = await res.json()
        interface CompanyApi {
          id: string | number
          name: string
          letterhead_base64?: string | null
          document_title?: string | null
        }
        const mapped: Company[] = (data as CompanyApi[]).map((c: CompanyApi) => ({
          id: String(c.id),
          name: c.name,
          letterheadName: c.letterhead_base64
            ? `${c.letterhead_base64.substring(0, 40)}...`
            : 'Nessun file',
          documentTitle: c.document_title ? c.document_title : '',
        }))
        setCompanies(mapped)
      } else {
        console.error('Failed to fetch companies', res.status)
      }
    } catch (err) {
      console.error('Error fetching companies', err)
    }
  }

  useEffect(() => {
    fetchCompanies()
  }, [])

  // Fetch PDF as ArrayBuffer when pdfUrl changes to avoid iframe/CORS issues.
  const fetchPdfData = async (signal?: AbortSignal) => {
    if (!pdfUrl) return
    setPdfFetchError(null)
    try {
      const resp = await fetch(pdfUrl, { signal, mode: 'cors' })
      if (!resp.ok) {
        const msg = `Could not fetch PDF for preview (status ${resp.status})`
        console.warn(msg)
        setPdfData(null)
        setPdfFetchError(msg)
        return
      }
      const ab = await resp.arrayBuffer()
      setPdfData(new Uint8Array(ab))
    } catch (err: unknown) {
      const e = err as { name?: string; message?: string }
      if (e && e.name === 'AbortError') return
      console.error('Error fetching PDF for viewer fallback:', err)
      setPdfData(null)
      setPdfFetchError(e?.message || String(err))
    }
  }

  useEffect(() => {
    if (!pdfUrl) {
      setPdfData(null)
      setPdfFetchError(null)
      return
    }
    const ac = new AbortController()
    fetchPdfData(ac.signal)
    return () => ac.abort()
  }, [pdfUrl, fetchPdfData])

  const retryFetchPdf = () => {
    setPdfFetchError(null)
    setPdfData(null)
    // trigger fetchPdfData directly
    fetchPdfData()
  }

  // Confirmation modal state + handlers
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmDeleteName, setConfirmDeleteName] = useState<string | null>(
    null
  )

  const openConfirmDelete = (companyId: string, companyName?: string) => {
    setConfirmDeleteId(companyId)
    setConfirmDeleteName(companyName || null)
  }

  const cancelConfirmDelete = () => {
    setConfirmDeleteId(null)
    setConfirmDeleteName(null)
  }

  const performConfirmedDelete = async () => {
    if (!confirmDeleteId) return
    try {
      const res = await fetchWithAuth(`/company/document-layout/${confirmDeleteId}/`, {
        method: 'DELETE',
      })
      if (res.status === 204 || res.ok) {
        setCompanies((prev) => prev.filter((c) => c.id !== confirmDeleteId))
        if (selectedCompanyId === confirmDeleteId) setSelectedCompanyId('')
        cancelConfirmDelete()
      } else {
        const txt = await res.text()
        console.error('Failed to delete company', res.status, txt)
        cancelConfirmDelete()
      }
    } catch (err) {
      console.error('Error deleting company', err)
      cancelConfirmDelete()
    }
  }

  const handleContextFileChange = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]

      // Accept only PDFs
      const isPdf =
        file.type === 'application/pdf' ||
        file.name.toLowerCase().endsWith('.pdf')
      if (!isPdf) {
        // lightweight feedback — you can replace with a nicer UI toast
        e.currentTarget.value = ''
        return
      }

      try {
        const fileData = await readFile(file)
        setContextFiles((prev) => [...prev, fileData])
      } catch (err) {
        console.error('Error reading file', err)
      }
    }
  }

  const handleGenerate = async () => {
    if (!instructions.trim()) return
    setLoading(true)
    setPdfUrl(null)
    setWordUrl(null)

    const filesForApi = contextFiles.map((f) => ({
      name: f.name,
      mimeType: f.type,
      data: f.data,
    }))

    const formData = new FormData()
    formData.append('doc_type', docType)
    formData.append('instructions', instructions)

    if (filesForApi.length > 0) {
      formData.append('context_files', JSON.stringify(filesForApi))
    }

    try {
      const res = await fetchWithAuth('/openai/draft/generate/', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        console.error('Generate document failed', res.status)
        setLoading(false)
        return
      }

      const data = await res.json()
      const gen = data.generated_document || data.generated || data.text || ''

      // Normalize generated result into an object with content and optional title
      type GeneratedObj = { contenuto?: string; content?: string; text?: string; titolo?: string; title?: string }
      let genObj: GeneratedObj = {}
      if (gen && typeof gen === 'object') {
        genObj = gen as GeneratedObj
      } else {
        genObj = { contenuto: String(gen) }
      }

      const content = genObj.contenuto || genObj.content || genObj.text || ''
      const title = genObj.titolo || genObj.title || docType || ''


      // Call export endpoint to generate PDF and Word
      try {
        interface ExportPayload {
          tipo_documento: string
          titolo: string
          contenuto: string
          note: string
          company_id?: string
        }
        const payload: ExportPayload = {
          tipo_documento: docType || title || 'document',
          titolo: title || docType || 'Documento',
          contenuto: content,
          note: '',
        }
        if (selectedCompanyId) payload.company_id = selectedCompanyId
        const expRes = await fetchWithAuth('/openai/draft/export/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })

        if (expRes && expRes.ok) {
          const expJson = await expRes.json()
          const urls = expJson.urls || {}
          if (urls.pdf) setPdfUrl(urls.pdf)
          if (urls.word) setWordUrl(urls.word)
        } else {
          const errText = await (expRes
            ? expRes.text()
            : Promise.resolve('no response'))
          console.error('Export failed', errText)
        }
      } catch (err: unknown) {
        console.error('Error exporting files', err)
      }
    } catch (err: unknown) {
      console.error('Error generating document', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAddCompany = () => {
    if (!newCompanyName.trim()) return
    // Prepare payload
    interface CreateCompanyPayload {
      name: string
      document_title: string
      letterhead_base64: string
      word_letterhead_base64: string
    }
    const payload: CreateCompanyPayload = { name: newCompanyName, document_title: '', letterhead_base64: '', word_letterhead_base64: '' }
    // include document title when creating company
    payload.document_title = newCompanyDocumentTitle || ''
    if (newCompanyFileData && newCompanyFileMime) {
      payload.letterhead_base64 = `data:${newCompanyFileMime};base64,${newCompanyFileData}`
    } else {
      payload.letterhead_base64 = ''
    }
    if (newCompanyWordFileData && newCompanyWordFileMime) {
      payload.word_letterhead_base64 = `data:${newCompanyWordFileMime};base64,${newCompanyWordFileData}`
    } else {
      payload.word_letterhead_base64 = ''
    }

    ; (async () => {
      try {
        const res = await fetchWithAuth('/company/document-layout/', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        if (res.ok || res.status === 201) {
          const created = await res.json()
          const added: Company = {
            id: String(created.id),
            name: created.name,
            documentTitle: created.document_title
              ? `${created.document_title.substring(0, 40)}...`
              : 'Nessun file',
          }
          setCompanies((prev) => [added, ...prev])
          setNewCompanyName('')
          setNewCompanyDocumentTitle('')
          setNewCompanyFile(null)
          setNewCompanyFileData(null)
          setNewCompanyFileMime(null)
          setNewCompanyWordFile(null)
          setNewCompanyWordFileData(null)
          setNewCompanyWordFileMime(null)
          setIsModalOpen(false)
        } else {
          const err = await res.text()
          console.error('Failed to create company', res.status, err)
        }
      } catch (err: unknown) {
        console.error('Error creating company', err)
      }
    })()
  }

  return (
    <div className="flex flex-col h-full bg-[#F8FAFC] text-sm">
      {/* Header */}
      <div className="px-7 py-8 bg-white border-b border-slate-300 flex-shrink-0">
        <div className="max-w-7xl mx-auto w-full">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <button
                onClick={() => navigate('/')}
                className="mr-6 p-2 hover:bg-slate-100 rounded-full transition-colors lg:hidden"
              >
                <ArrowLeft className="w-5 h-5 text-slate-600" />
              </button>
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  Generatore Documenti
                </h2>
                <p className="text-slate-500 font-light mt-1 text-sm">
                  Redazione automatica di bozze legali avanzate
                </p>
              </div>
            </div>
          </div>

          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('GENERATE')}
              className={`pb-3 text-sm font-medium border-b-2 transition-all tracking-wide ${activeTab === 'GENERATE'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
            >
              WORKSPACE
            </button>
            <button
              onClick={() => setActiveTab('ADD_COMPANY')}
              className={`pb-3 text-sm font-medium border-b-2 transition-all tracking-wide ${activeTab === 'ADD_COMPANY'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
            >
              AGGIUNGI AZIENDA
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-7xl mx-auto h-full">
          {activeTab === 'GENERATE' ? (
            <div className="flex flex-col lg:flex-row gap-8 h-full">
              {/* Inputs Panel */}
              <div className="w-full lg:w-[450px] flex-shrink-0 flex flex-col gap-6 overflow-y-auto h-full pr-2 pb-10">
                <div className="bg-white rounded-sm border border-slate-300 p-8 shadow-sm flex-shrink-0">
                  <div className="mb-6">
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                      Società Emittente
                    </label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-3.5 w-4 h-4 text-slate-400" />
                      <select
                        value={selectedCompanyId}
                        onChange={(e) => setSelectedCompanyId(e.target.value)}
                        className="w-full pl-10 border border-slate-300 rounded-md px-3 py-2 text-sm bg-slate-50 focus:bg-white focus:ring-1 focus:ring-slate-400 focus:border-slate-400 outline-none transition-all appearance-none text-slate-700 font-medium"
                      >
                        <option value="">Nessuna (Bozza generica)</option>
                        {companies.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="mb-6">
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Tipologia Documento
                    </label>
                    <div className="relative">
                      <FileText className="absolute left-3 top-3.5 w-4 h-4 text-slate-400" />
                      <select
                        value={docType}
                        onChange={(e) => setDocType(e.target.value)}
                        className="w-full pl-10 border border-slate-300 rounded-md px-3 py-2 text-sm bg-slate-50 focus:bg-white focus:ring-1 focus:ring-slate-400 focus:border-slate-400 outline-none transition-all appearance-none text-slate-700 font-medium"
                      >
                        <option value="">Personalizzato / Altro</option>
                        <option value="Addendum Contrattuale">Ad dendum Contrattuale</option>
                        <option value="Contratto di Servizi">Contratto di Servizi</option>
                        <option value="Diffida ad Adempiere">Diffida ad Adempiere</option>
                        <option value="Lettera di Convocazione">Lettera di Convocazione</option>
                        <option value="Lettera di Incarico">Lettera di Incarico</option>
                        <option value="NDA">Non-Disclosure Agreement (NDA)</option>
                        <option value="Parere Legale">Parere Legale</option>
                        <option value="Parere Legale">Parere Legale Pro Veritate</option>
                        <option value="Verbale Assemblea Ordinaria">Verbale Assemblea Ordinaria</option>
                        <option value="Verbale Consiglio di Amministrazione">Verbale CdA</option>
                      </select>
                    </div>
                  </div>

                  <div className="mb-2">
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Contesto
                    </label>
                    <div
                      onClick={() => fileInputRef.current?.click()}
                      className="border-2 border-dashed border-slate-300 rounded-md p-5 flex items-center justify-center cursor-pointer hover:bg-slate-50 transition-colors group"
                    >
                      <Upload className="w-5 h-5 text-slate-400 group-hover:text-slate-600 mr-3" />
                      <span className="text-sm text-slate-500 group-hover:text-slate-700">
                        Carica file (PDF)
                      </span>
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        onChange={handleContextFileChange}
                        accept=".pdf,application/pdf"
                      />
                    </div>
                    {contextFiles.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {contextFiles.map((f, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between text-sm text-slate-700 bg-white border border-slate-300 px-3 py-2 rounded-md"
                          >
                            <span className="truncate font-medium">
                              {f.name}
                            </span>
                            <button
                              onClick={() =>
                                setContextFiles((files) =>
                                  files.filter((_, idx) => idx !== i)
                                )
                              }
                            >
                              <X className="w-5 h-5 text-slate-400 hover:text-red-600" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex-1 bg-white rounded-sm border border-slate-300 p-8 shadow-sm flex flex-col min-h-[300px] flex-shrink-0">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    Istruzioni Prompt
                  </label>
                  <textarea
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    placeholder="Descrivi in dettaglio il contenuto, le clausole specifiche e il tono del documento..."
                    className="w-full flex-1 border-0 bg-transparent outline-none resize-none text-sm text-slate-800 placeholder-slate-300 font-light leading-relaxed"
                  />
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={loading || !instructions.trim()}
                  className="w-full bg-[#0F172A] text-white font-medium py-4 rounded-sm shadow-lg hover:bg-black transition-all flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed tracking-wide text-xs flex-shrink-0"
                >
                  {loading ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : (
                    <Sparkles className="w-6 h-6 mr-3 text-[#C5A572]" />
                  )}
                  {loading ? 'ELABORAZIONE IN CORSO...' : 'GENERA BOZZA'}
                </button>
              </div>

              {/* Preview Panel */}
              <div className="flex-1 bg-white rounded-sm border border-slate-300 p-8 shadow-sm overflow-y-auto">
                {pdfUrl ? (
                  <div className="relative h-full">
                    <div className="absolute top-3 right-3 flex gap-2 z-10">
                      {pdfUrl && (
                        <a
                          href={pdfUrl}
                          download={`${docType || 'doc'}_${new Date().toISOString().slice(0, 10)}.pdf`}
                          className="p-1.5 bg-white hover:bg-red-50 text-red-600 rounded border border-red-200 shadow-sm text-xs flex items-center gap-2"
                        >
                          <FileDown className="w-4 h-4" />
                          <span className="text-xs font-bold">PDF</span>
                        </a>
                      )}
                      {wordUrl && (
                        <a
                          href={wordUrl}
                          download={`${docType || 'doc'}_${new Date().toISOString().slice(0, 10)}.docx`}
                          className="p-1.5 bg-white hover:bg-blue-50 text-blue-600 rounded border border-blue-200 shadow-sm text-xs flex items-center gap-2"
                        >
                          <FileDown className="w-4 h-4" />
                          <span className="text-xs font-bold">WORD</span>
                        </a>
                      )}
                    </div>

                    <div className="h-full">
                      {pdfFetchError ? (
                        <div className="h-[100vh] flex flex-col items-center justify-center">
                          <div className="bg-red-600 text-white px-4 py-2 rounded mb-4">
                            {pdfFetchError}
                          </div>
                          <div className="flex gap-3">
                            <a
                              href={pdfUrl as string}
                              target="_blank"
                              rel="noreferrer"
                              className="px-4 py-2 bg-white border rounded text-sm"
                            >
                              Apri PDF in nuova scheda
                            </a>
                            <button
                              onClick={retryFetchPdf}
                              className="px-4 py-2 bg-blue-600 text-white rounded text-sm"
                            >
                              Riprova
                            </button>
                          </div>
                        </div>
                      ) : (
                        <Worker workerUrl={pdfWorkerUrl}>
                          <div style={{ height: '105vh  ' }}>
                            <Viewer fileUrl={pdfData ?? (pdfUrl as string)} />
                          </div>
                        </Worker>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
                    <FileText className="w-16 h-16 mb-6 text-slate-300" />
                    <h3 className="text-xl text-slate-400 mb-3">
                      Area Anteprima
                    </h3>
                    <p className="max-w-xs text-slate-400 font-light text-sm">
                      Il documento generato apparirà direttamente qui come anteprima PDF.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            // COMPANY MANAGEMENT
            <div className="max-w-4xl mx-auto">
              <div className="bg-white rounded-sm border border-slate-300 p-8 shadow-sm min-h-[500px]">
                <div className="flex justify-between items-center mb-10 border-b border-slate-200 pb-8">
                  <h3 className="text-xl font-medium text-slate-900">
                    Società Configurate
                  </h3>
                  <button
                    onClick={() => setIsModalOpen(true)}
                    className="bg-slate-900 text-white px-6 py-2 rounded-sm text-sm font-medium hover:bg-black flex items-center transition-colors shadow-md"
                  >
                    <Plus className="w-5 h-5 mr-2" />
                    Aggiungi Azienda
                  </button>
                </div>

                {companies.length === 0 ? (
                  <div className="text-center py-24">
                    <Building2 className="w-20 h-20 mx-auto mb-6 text-slate-200" />
                    <p className="text-slate-400 font-light text-xl">
                      Nessuna anagrafica presente.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {companies.map((company) => (
                      <div
                        key={company.id}
                        className="relative border border-slate-300 p-8 hover:border-slate-500 transition-colors bg-slate-50 group cursor-pointer"
                      >
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            openConfirmDelete(company.id, company.name)
                          }}
                          className="absolute right-3 top-3 text-slate-400 hover:text-red-600 p-1 rounded"
                          title="Elimina azienda"
                        >
                          <Trash className="w-4 h-4" />
                        </button>
                        <div className="flex items-center mb-6">
                          <div className="w-12 h-12 bg-white border border-slate-300 text-slate-800 flex items-center justify-center font-bold text-xl mr-5 shadow-sm">
                            {company.name.substring(0, 1).toUpperCase()}
                          </div>
                          <div>
                            <h4 className="font-semibold text-lg text-slate-900 mb-1">
                              {company.name}
                            </h4>
                            <span className="text-xs text-[#C5A572] font-bold uppercase tracking-wider">
                              Attiva
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center text-sm text-slate-500 mt-4 pt-6 border-t border-slate-200">
                          <FileText className="w-5 h-5 mr-3" />
                          <span className="truncate">
                            {company.documentTitle}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900 bg-opacity-80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white shadow-2xl max-w-lg w-full p-10 animate-in fade-in zoom-in duration-200 rounded-sm h-500 overflow-y-auto max-h-full">
            <div className="flex justify-between items-center mb-10">
              <h3 className="text-3xl text-slate-900">
                Nuova Anagrafica
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-slate-900 transition-colors"
              >
                <X className="w-7 h-7" />
              </button>
            </div>

            <div className="space-y-8">
              <div>
                <label className="block text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
                  Nome Azienda
                </label>
                <input
                  type="text"
                  className="w-full border-b border-slate-300 px-0 py-3 outline-none focus:border-slate-900 text-xl bg-transparent placeholder-gray-300 transition-colors"
                  placeholder="Es. Studio Legale Associato"
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                />
              </div>

              {/* document title is taken from uploaded file name; no manual input */}

              <div>
                <label className="block text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
                  Carta Intestata (PDF)
                </label>
                <div
                  onClick={() => companyFileRef.current?.click()}
                  className="border-2 border-dashed border-slate-300 bg-slate-50 p-10 flex flex-col items-center justify-center cursor-pointer hover:bg-white hover:border-slate-500 transition-all text-center"
                >
                  {newCompanyFile ? (
                    <>
                      <Check className="w-10 h-10 text-emerald-600 mb-3" />
                      <span className="text-base font-medium text-slate-900">
                        {newCompanyFile}
                      </span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-10 h-10 text-slate-300 mb-3" />
                      <span className="text-base text-slate-500">
                        Trascina o clicca per caricare (.pdf)
                      </span>
                    </>
                  )}
                  <input
                    ref={companyFileRef}
                    type="file"
                    className="hidden"
                    accept="application/pdf"
                    onChange={async (e) => {
                      if (e.target.files?.[0]) {
                        const f = e.target.files[0]
                        try {
                          const fileData = await readFile(f)
                          setNewCompanyFile(f.name)
                          // set document title from filename (without extension)
                          const title = f.name.replace(/\.[^/.]+$/, '')
                          setNewCompanyDocumentTitle(title)
                          setNewCompanyFileData(fileData.data)
                          setNewCompanyFileMime(f.type)
                        } catch (err) {
                          console.error('Error reading company file', err)
                        }
                      }
                    }}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
                  Carta Intestata (Word)
                </label>
                <div
                  onClick={() => companyWordFileRef.current?.click()}
                  className="border-2 border-dashed border-slate-300 bg-slate-50 p-10 flex flex-col items-center justify-center cursor-pointer hover:bg-white hover:border-slate-500 transition-all text-center"
                >
                  {newCompanyWordFile ? (
                    <>
                      <Check className="w-10 h-10 text-emerald-600 mb-3" />
                      <span className="text-base font-medium text-slate-900">
                        {newCompanyWordFile}
                      </span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-10 h-10 text-slate-300 mb-3" />
                      <span className="text-base text-slate-500">
                        Trascina o clicca per caricare (.docx)
                      </span>
                    </>
                  )}
                  <input
                    ref={companyWordFileRef}
                    type="file"
                    className="hidden"
                    accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={async (e) => {
                      if (e.target.files?.[0]) {
                        const f = e.target.files[0]
                        try {
                          const fileData = await readFile(f)
                          setNewCompanyWordFile(f.name)
                          // set document title from filename (without extension)
                          const title = f.name.replace(/\.[^/.]+$/, '')
                          setNewCompanyDocumentTitle(title)
                          setNewCompanyWordFileData(fileData.data)
                          setNewCompanyWordFileMime(f.type)
                        } catch (err) {
                          console.error('Error reading company word file', err)
                        }
                      }
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-12 flex gap-5">
              <button
                onClick={() => setIsModalOpen(false)}
                className="flex-1 px-6 py-4 border border-slate-300 text-slate-600 hover:bg-slate-50 font-medium tracking-wide text-sm uppercase"
              >
                ANNULLA
              </button>
              <button
                onClick={handleAddCompany}
                disabled={!newCompanyName.trim()}
                className="flex-1 px-6 py-4 bg-[#0F172A] text-white hover:bg-black font-medium tracking-wide text-sm disabled:opacity-50 uppercase shadow-md"
              >
                SALVA
              </button>
            </div>
          </div>
        </div>
      )}
      {/* CONFIRM DELETE MODAL */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-slate-900 bg-opacity-80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white shadow-2xl max-w-md w-full p-8 animate-in fade-in duration-200 rounded-sm">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-2xl font-semibold text-slate-900">
                Conferma eliminazione
              </h3>
              <button
                onClick={cancelConfirmDelete}
                className="text-gray-400 hover:text-slate-900 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            <p className="text-sm text-slate-700">
              Sei sicuro di voler eliminare <strong>{confirmDeleteName}</strong>
              ? Questa azione è irreversibile e rimuoverà definitivamente
              l'anagrafica.
            </p>
            <div className="mt-6 flex justify-end gap-4">
              <button
                onClick={cancelConfirmDelete}
                className="px-4 py-2 border border-slate-300 rounded text-sm text-slate-700 hover:bg-slate-50"
              >
                Annulla
              </button>
              <button
                onClick={performConfirmedDelete}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700"
              >
                Elimina
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
