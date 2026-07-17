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
    <div className="page-root h-screen flex flex-row overflow-hidden bg-[#f8fafc]">
      {/* Pannello Sinistro */}
      <div className="w-[420px] shrink-0 bg-white border-r border-slate-100 flex flex-col h-full overflow-y-auto">
        <div className="px-6 py-5 border-b border-slate-100 flex gap-6 shrink-0">
          <button
            onClick={() => setActiveTab('GENERATE')}
            className={`text-[15px] pb-1 transition-all ${
              activeTab === 'GENERATE'
                ? 'text-[#1e3a8a] font-semibold border-b-2 border-[#1e3a8a]'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            Genera documento
          </button>
          <button
            onClick={() => setActiveTab('ADD_COMPANY')}
            className={`text-[15px] pb-1 transition-all ${
              activeTab === 'ADD_COMPANY'
                ? 'text-[#1e3a8a] font-semibold border-b-2 border-[#1e3a8a]'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            Aggiungi azienda
          </button>
        </div>

        <div className="p-6 flex flex-col flex-1">
          {activeTab === 'GENERATE' ? (
            <div className="flex flex-col flex-1 h-full">
              <div className="mb-5">
                <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                  Società Emittente
                </label>
                <select
                  value={selectedCompanyId}
                  onChange={(e) => setSelectedCompanyId(e.target.value)}
                  className="apple-select w-full"
                >
                  <option value="">Nessuna (Bozza generica)</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mb-5">
                <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                  Tipologia Documento
                </label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="apple-select w-full"
                >
                  <option value="">Personalizzato / Altro</option>
                  <option value="Addendum Contrattuale">Addendum Contrattuale</option>
                  <option value="Contratto di Servizi">Contratto di Servizi</option>
                  <option value="Diffida ad Adempiere">Diffida ad Adempiere</option>
                  <option value="Lettera di Convocazione">Lettera di Convocazione</option>
                  <option value="Lettera di Incarico">Lettera di Incarico</option>
                  <option value="NDA">Non-Disclosure Agreement (NDA)</option>
                  <option value="Parere Legale">Parere Legale</option>
                  <option value="Parere Legale Pro Veritate">Parere Legale Pro Veritate</option>
                  <option value="Verbale Assemblea Ordinaria">Verbale Assemblea Ordinaria</option>
                  <option value="Verbale Consiglio di Amministrazione">Verbale CdA</option>
                </select>
              </div>

              <div className="mb-5">
                <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                  Contesto (PDF)
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl p-6 text-center hover:border-[#1e3a8a] cursor-pointer transition-colors"
                >
                  <Upload className="w-6 h-6 text-slate-400 mx-auto mb-2" />
                  <span className="text-[13px] text-slate-500">Carica file</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleContextFileChange}
                    accept=".pdf,application/pdf"
                  />
                </div>
                {contextFiles.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {contextFiles.map((f, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-lg"
                      >
                        <span className="truncate max-w-[200px]">{f.name}</span>
                        <button
                          onClick={() =>
                            setContextFiles((files) => files.filter((_, idx) => idx !== i))
                          }
                          className="text-slate-400 hover:text-red-500"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mb-6 flex-1 flex flex-col">
                <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                  Istruzioni Prompt
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="Descrivi in dettaglio il contenuto, le clausole specifiche e il tono del documento..."
                  rows={5}
                  className="apple-input w-full flex-1 resize-none min-h-[120px]"
                />
              </div>

              <div className="mt-auto space-y-3 shrink-0">
                <button
                  onClick={handleGenerate}
                  disabled={loading || !instructions.trim()}
                  className="btn-primary w-full justify-center"
                >
                  {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  ) : (
                    <Sparkles className="w-5 h-5 mr-2" />
                  )}
                  {loading ? 'Elaborazione...' : 'Genera bozza'}
                </button>
                {wordUrl && (
                  <a
                    href={wordUrl}
                    download={`${docType || 'doc'}_${new Date().toISOString().slice(0, 10)}.docx`}
                    className="btn-secondary w-full justify-center flex items-center"
                  >
                    <FileDown className="w-4 h-4 mr-2" />
                    Scarica Word
                  </a>
                )}
                {pdfUrl && (
                  <a
                    href={pdfUrl}
                    download={`${docType || 'doc'}_${new Date().toISOString().slice(0, 10)}.pdf`}
                    className="btn-secondary w-full justify-center flex items-center"
                  >
                    <FileDown className="w-4 h-4 mr-2" />
                    Scarica PDF
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <div className="mb-8">
                <h3 className="text-[13px] font-medium text-slate-600 mb-3 uppercase tracking-wider">
                  Aziende salvate
                </h3>
                {companies.length === 0 ? (
                  <p className="text-sm text-slate-400">Nessuna azienda.</p>
                ) : (
                  <div className="space-y-2">
                    {companies.map((company) => (
                      <div
                        key={company.id}
                        className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100"
                      >
                        <div>
                          <p className="text-sm font-medium text-slate-800">{company.name}</p>
                          {company.documentTitle && (
                            <p className="text-xs text-slate-500 truncate max-w-[200px]">
                              {company.documentTitle}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => openConfirmDelete(company.id, company.name)}
                          className="p-1.5 text-red-400 hover:bg-red-50 rounded-md transition-colors"
                        >
                          <Trash className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="border-t border-slate-100 pt-6">
                <h3 className="text-[13px] font-medium text-slate-600 mb-4 uppercase tracking-wider">
                  Nuova Azienda
                </h3>

                <div className="mb-4">
                  <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                    Nome Azienda
                  </label>
                  <input
                    type="text"
                    className="apple-input w-full"
                    placeholder="Es. Studio Legale"
                    value={newCompanyName}
                    onChange={(e) => setNewCompanyName(e.target.value)}
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                    Carta Intestata (PDF)
                  </label>
                  <div
                    onClick={() => companyFileRef.current?.click()}
                    className="bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl p-4 text-center hover:border-[#1e3a8a] cursor-pointer transition-colors"
                  >
                    {newCompanyFile ? (
                      <div className="flex flex-col items-center">
                        <Check className="w-5 h-5 text-green-500 mb-1" />
                        <span className="text-xs text-slate-600 truncate max-w-full px-2">
                          {newCompanyFile}
                        </span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center">
                        <Upload className="w-5 h-5 text-slate-400 mb-1" />
                        <span className="text-[13px] text-slate-500">Carica PDF</span>
                      </div>
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

                <div className="mb-6">
                  <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                    Carta Intestata (Word)
                  </label>
                  <div
                    onClick={() => companyWordFileRef.current?.click()}
                    className="bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl p-4 text-center hover:border-[#1e3a8a] cursor-pointer transition-colors"
                  >
                    {newCompanyWordFile ? (
                      <div className="flex flex-col items-center">
                        <Check className="w-5 h-5 text-green-500 mb-1" />
                        <span className="text-xs text-slate-600 truncate max-w-full px-2">
                          {newCompanyWordFile}
                        </span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center">
                        <Upload className="w-5 h-5 text-slate-400 mb-1" />
                        <span className="text-[13px] text-slate-500">Carica DOCX</span>
                      </div>
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

                <button
                  onClick={handleAddCompany}
                  disabled={!newCompanyName.trim()}
                  className="btn-primary w-full justify-center mt-auto"
                >
                  Salva Azienda
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Pannello Destro */}
      <div className="flex-1 bg-[#f8fafc] flex flex-col items-center justify-center h-full relative overflow-hidden">
        <button
          onClick={() => navigate('/')}
          className="absolute top-5 left-5 p-2 bg-white rounded-full shadow-sm hover:bg-slate-50 transition-colors z-10"
          title="Torna alla Home"
        >
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </button>

        {pdfUrl ? (
          <div className="w-full h-full bg-white flex flex-col">
            {pdfFetchError ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
                  <X className="w-6 h-6 text-red-600" />
                </div>
                <p className="text-red-600 font-medium mb-4">{pdfFetchError}</p>
                <div className="flex gap-3 justify-center">
                  <button onClick={retryFetchPdf} className="btn-primary">
                    Riprova
                  </button>
                  <a href={pdfUrl} target="_blank" rel="noreferrer" className="btn-secondary">
                    Apri in nuova scheda
                  </a>
                </div>
              </div>
            ) : (
              <Worker workerUrl={pdfWorkerUrl}>
                <div className="flex-1 overflow-auto rounded-none">
                  <Viewer fileUrl={pdfData ?? pdfUrl} />
                </div>
              </Worker>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center px-6">
            <FileText className="w-12 h-12 text-slate-300 mb-4" />
            <p className="text-slate-400 text-sm font-medium">
              Genera un documento per visualizzare l'anteprima
            </p>
          </div>
        )}
      </div>

      {/* MODAL ELIMINAZIONE */}
      {confirmDeleteId && (
        <div className="modal-overlay flex items-center justify-center z-50">
          <div className="modal-box w-full max-w-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Conferma eliminazione</h3>
            <p className="text-sm text-slate-600 mb-6">
              Sei sicuro di voler eliminare <strong>{confirmDeleteName}</strong>? Questa azione è
              irreversibile.
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={cancelConfirmDelete} className="btn-secondary">
                Annulla
              </button>
              <button onClick={performConfirmedDelete} className="btn-danger">
                Elimina
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
