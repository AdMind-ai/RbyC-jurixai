
import React, { useState, useRef } from 'react';
import { Company } from '../../types/types';
import { Sparkles, FileText, RefreshCw, AlertCircle, Upload, X, File as FileIcon, FileDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { fetchWithAuth } from '../../api/fetchWithAuth';
import { geminiService } from '../../services/geminiService';
import { Viewer, Worker } from '@react-pdf-viewer/core';
import '@react-pdf-viewer/core/lib/styles/index.css';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import { zoomPlugin } from '@react-pdf-viewer/zoom';
import '../../styles/DocumentGeneratorViewer.css';
// Vite: import pdf.worker as an asset so dev server serves it correctly
import '@react-pdf-viewer/zoom/lib/styles/index.css';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.js?url';


interface AttachedFile {
  name: string;
  mimeType: string;
  data: string; // base64
}

const DocumentGenerator: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  // Fetch companies from backend API
  React.useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const res = await fetchWithAuth('/companies/', { method: 'GET' });
        if (res.ok) {
          const data = await res.json();
          setCompanies(data.map((c: Company) => ({
            id: c.id.toString(),
            name: c.name,
            vatNumber: c.vat_number,
            type: c.company_type,
            address: c.address,
            capital: Number(c.capital),
            status: c.status,
            officers: c.officers || [],
            shareholders: c.shareholders || [],
            letterheadInfo: c.letterhead_info,
            letterheadFile: c.letterhead_file,
            nextMeetingDate: c.next_meeting_date,
          })));
        }
      } catch (err) {
        setCompanies([]);
        console.error('Errore nel fetch delle società:', err);
      }
    };
    fetchCompanies();
  }, []);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('');
  const [docType, setDocType] = useState<string>('');
  const [details, setDetails] = useState<string>('');
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [generatedContent, setGeneratedContent] = useState<string>('');
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  // react-pdf-viewer plugin instance
  const defaultLayoutPluginInstance = defaultLayoutPlugin();
  const zoomPluginInstance = zoomPlugin();
  const { ZoomInButton, ZoomOutButton, CurrentScale } = zoomPluginInstance;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];

      // Check size (limit to 4MB for demo)
      if (file.size > 4 * 1024 * 1024) {
        setError('Il file è troppo grande. Massimo 4MB.');
        return;
      }

      const reader = new FileReader();
      console.log('File MIME type:', file.type);
      reader.onloadend = () => {
        const base64String = (reader.result as string).split(',')[1];
        setAttachedFiles(prev => [...prev, {
          name: file.name,
          mimeType: file.type || 'application/octet-stream',
          data: base64String
        }]);
        setError('');
      };
      reader.readAsDataURL(file);
    }
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleGenerate = async () => {
    // Removed mandatory company check
    if (!docType && !details.trim()) {
        setError('Se non selezioni un tipo di documento, devi fornire delle istruzioni nei dettagli.');
        return;
    }
    
    setError('');
    setIsLoading(true);
    setGeneratedContent('');

    const company = selectedCompanyId ? companies.find(c => c.id === selectedCompanyId) || null : null;
    
    const result = await geminiService.generateDocument(docType, company, details, attachedFiles);
    // Clear previous pdf preview while generating
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
      setPdfUrl(null);
    }

    // Now request backend to render PDF combining company layout and generated content
    try {
      const payload = { company_id: company ? company.id : null, markdown: result };
      const res = await fetchWithAuth('/documents/generate-pdf/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res && res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        
        // Record usage for document generation
        fetchWithAuth('/usage/manual/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: 'SEGRETERIA_SOCIETARIA',
            subTool: 'DOCUMENTI_AI',
            quantity: 1, // 1 documento generato = 1 usi
          }),
        });

        setPdfUrl(url);
      } else {
        const errText = await res.text();
        setError('Errore nella generazione PDF: ' + errText);
        // show markdown fallback so user can inspect the content if PDF failed
        setGeneratedContent(result);
      }
    } catch (err) {
      console.error('Error creating PDF:', err);
      setError('Errore nella generazione del PDF.');
      // show markdown fallback on exception
      setGeneratedContent(result);
    }

    setIsLoading(false);
  };

  return (
    <div className="w-full h-full p-6 flex flex-col gap-5 animate-fade-in max-w-5xl mx-auto">
      <div className="border-b border-slate-300 pb-3 mb-2">
        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Sparkles className="text-purple-600" />
          Generatore Documenti AI
        </h2>
        <p className="text-slate-500 text-sm">Redazione automatica di bozze legali</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
        {/* Input Panel */}
        <div className="lg:w-1/3 bg-white rounded-lg shadow-sm border border-slate-300 p-4 flex flex-col gap-3 overflow-auto">

          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm flex items-start gap-2 border border-red-100">
              <AlertCircle size={16} className="mt-0.5" />
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Società</label>
            <select
              className="w-full p-2 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
              value={selectedCompanyId}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
            >
              <option value="">-- Nessuna (Generico) --</option>
              {companies.map(c => (
                <option key={c.id} value={c.id}>{c.name} ({c.type})</option>
              ))}
            </select>
            <p className="text-[11px] text-slate-400 mt-1">Lascia vuoto per documenti generici o non legati a una società censita.</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo Documento (Opzionale)</label>
            <select
              className="w-full p-2 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
            >
              <option value="">-- Personalizzato / Istruzioni libere --</option>
              <option value="Verbale Assemblea Ordinaria">Verbale Assemblea Ordinaria</option>
              <option value="Verbale Consiglio di Amministrazione">Verbale CdA</option>
              <option value="Lettera di Convocazione">Lettera di Convocazione</option>
              <option value="Addendum Contrattuale">Addendum Contrattuale</option>
              <option value="Parere Legale">Parere Legale</option>
              <option value="Diffida ad Adempiere">Diffida ad Adempiere</option>
            </select>
          </div>

          {/* File Upload Section */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Documenti di Contesto</label>
            <div className="space-y-1.5">
              {attachedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-slate-50 p-1.5 rounded border border-slate-300 text-xs">
                  <div className="flex items-center gap-2 truncate">
                    <FileIcon size={14} className="text-blue-500" />
                    <span className="truncate max-w-[180px]">{file.name}</span>
                  </div>
                  <button onClick={() => removeFile(index)} className="text-slate-400 hover:text-red-500">
                    <X size={16} />
                  </button>
                </div>
              ))}

              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".pdf,.txt,.doc,.docx,.md"
                onChange={handleFileChange}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full py-1.5 border-2 border-dashed border-slate-300 rounded-lg text-slate-500 hover:bg-slate-50 hover:border-blue-400 hover:text-blue-500 transition-colors text-xs flex items-center justify-center gap-2"
              >
                <Upload size={15} />
                Carica File Contesto
              </button>
            </div>
          </div>

          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-700 mb-1">Dettagli e Istruzioni *</label>
            <textarea
              className="w-full h-28 lg:h-[calc(100%-2rem)] p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none text-xs"
              placeholder={docType ? "Aggiungi dettagli specifici..." : "Descrivi qui il documento da generare in dettaglio..."}
              value={details}
              onChange={(e) => setDetails(e.target.value)}
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={isLoading}
            className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors shadow-md text-sm"
          >
            {isLoading ? (
              <>
                <RefreshCw className="animate-spin" size={17} />
                Generazione...
              </>
            ) : (
              <>
                <Sparkles size={17} />
                Genera Bozza
              </>
            )}
          </button>
        </div>

        {/* Preview Panel */}
        <div className="lg:w-2/3 bg-slate-50 rounded-lg shadow-inner border border-slate-300 p-4 flex flex-col relative overflow-hidden">
          {pdfUrl && (
            <div className="absolute top-3 right-3 flex gap-2 z-10">
              <a href={pdfUrl} download={`${docType || 'doc'}_${new Date().toISOString().slice(0,10)}.pdf`} className="p-1.5 bg-white hover:bg-blue-50 text-blue-600 rounded border border-blue-200 shadow-sm text-xs">
                <FileDown size={15} /> <span className="text-xs font-bold ml-1">PDF</span>
              </a>
            </div>
          )}

          <div className="flex-1 overflow-auto bg-white rounded-lg border border-slate-200 p-3 shadow-sm text-slate-800 text-sm">
            {pdfUrl ? (
              <div className="h-full">
                <div className="pdf-preview-card">
                  <div className="pdf-preview-header">
                    <div className="pdf-preview-title">
                      <span>Anteprima PDF</span>
                    </div>
                    <div className="pdf-preview-actions">
                      <div className="flex items-center gap-2">
                        <div className="pdf-zoom-controls">
                          <ZoomOutButton />
                          <span style={{ margin: '0 8px', fontWeight: 600 }}><CurrentScale /></span>
                          <ZoomInButton />
                        </div>
                      </div>
                      <a className="btn secondary" href={pdfUrl} target="_blank" rel="noreferrer">Apri</a>
                    </div>
                  </div>
                  <div className="pdf-preview-body">
                    <Worker workerUrl={pdfWorkerUrl as string}>
                      <div style={{ height: '72vh' }}>
                        <Viewer fileUrl={pdfUrl} plugins={[defaultLayoutPluginInstance, zoomPluginInstance]} />
                      </div>
                    </Worker>
                  </div>
                </div>
              </div>
            ) : generatedContent ? (
              <div className="markdown-body p-4">
                <ReactMarkdown>{generatedContent}</ReactMarkdown>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3 p-6">
                <FileText size={38} className="opacity-20" />
                <p className="text-center max-w-md text-xs">
                  Seleziona una società (opzionale), carica eventuali documenti e clicca su "Genera Bozza".
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentGenerator;
