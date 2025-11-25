
import React, { useState, useRef } from 'react';
import { Company } from '../../types/types';
import { Sparkles, FileText, Copy, RefreshCw, AlertCircle, Upload, X, File as FileIcon, FileDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { fetchWithAuth } from '../../api/fetchWithAuth';


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
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];

      // Check size (limit to 4MB for demo)
      if (file.size > 4 * 1024 * 1024) {
        setError('Il file è troppo grande. Massimo 4MB.');
        return;
      }

      const reader = new FileReader();
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


    const result = "Simulated generated document content"
    setGeneratedContent(result);

    setIsLoading(false);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedContent);
  };

  const downloadFile = (format: 'doc' | 'txt') => {
    if (!generatedContent) return;

    let content = generatedContent;
    let mimeType = 'text/plain';
    let extension = 'txt';

    if (format === 'doc') {
      // Simple HTML wrap for Word to interpret
      content = `
          <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
          <head><meta charset='utf-8'><title>Documento</title></head>
          <body>${generatedContent.replace(/\n/g, '<br>')}</body>
          </html>
        `;
      mimeType = 'application/msword';
      extension = 'doc';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `documento_${new Date().toISOString().slice(0, 10)}.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full h-full p-6 flex flex-col gap-5 animate-fade-in max-w-5xl mx-auto">
      <div className="border-b border-slate-300 pb-3 mb-2">
        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Sparkles className="text-purple-600" />
          Generatore Documenti AI
        </h2>
        <p className="text-slate-500 text-sm">Redazione automatica di bozze legali con Gemini 2.5 Flash</p>
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
          {generatedContent && (
            <div className="absolute top-3 right-3 flex gap-2 z-10">
              <button
                onClick={() => downloadFile('doc')}
                className="p-1.5 bg-white hover:bg-blue-50 text-blue-600 rounded border border-blue-200 shadow-sm text-xs"
                title="Scarica Word"
              >
                <FileDown size={15} /> <span className="text-xs font-bold ml-1">DOC</span>
              </button>
              <button
                onClick={() => downloadFile('txt')}
                className="p-1.5 bg-white hover:bg-slate-100 text-slate-600 rounded border border-slate-200 shadow-sm text-xs"
                title="Scarica TXT"
              >
                <FileDown size={15} /> <span className="text-xs font-bold ml-1">TXT</span>
              </button>
              <button
                onClick={copyToClipboard}
                className="p-1.5 bg-white hover:bg-slate-100 text-slate-600 rounded border border-slate-200 shadow-sm text-xs"
                title="Copia"
              >
                <Copy size={15} />
              </button>
            </div>
          )}

          <div className="flex-1 overflow-auto bg-white rounded-lg border border-slate-200 p-5 shadow-sm font-serif text-slate-800 leading-relaxed text-sm">
            {generatedContent ? (
              <div className="markdown-body">
                <ReactMarkdown>{generatedContent}</ReactMarkdown>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3">
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
