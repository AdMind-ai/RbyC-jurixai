
import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { Company } from '../types/types';
import { api } from "../api/api";
import * as pdfjsLib from 'pdfjs-dist/legacy/build/pdf'
import workerSrc from 'pdfjs-dist/legacy/build/pdf.worker?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

type ComplianceFile = {
  mimeType: string;
  data: string;
  name?: string;
};

type ComplianceDocumentMetric = {
  name?: string;
  mimeType?: string;
  pages: number;
};

const isPdfMimeType = (mimeType?: string) =>
  Boolean(mimeType && mimeType.toLowerCase().includes('pdf'));

const base64ToUint8Array = (input: string): Uint8Array => {
  const cleaned = (input || '').split(',').pop() ?? '';
  const binary = atob(cleaned);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
};

const countPdfPages = async (file: ComplianceFile): Promise<ComplianceDocumentMetric> => {
  if (!isPdfMimeType(file.mimeType) || !file.data) {
    return { name: file.name, mimeType: file.mimeType, pages: 0 };
  }
  try {
    const arrayBuffer = base64ToUint8Array(file.data);
    const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
    const pdf = await loadingTask.promise;
    const pages = pdf.numPages || 0;
    pdf.destroy();
    return { name: file.name, mimeType: file.mimeType, pages };
  } catch (err) {
    console.warn('Failed to count pages for file', file.name, err);
    return { name: file.name, mimeType: file.mimeType, pages: 0 };
  }
};

const recordComplianceUsage = async (
  totalPages: number,
  documents: ComplianceDocumentMetric[],
  norms: string[]
) => {
  if (totalPages <= 0) {
    return;
  }
  try {
    await api.post('/usage/manual/', {
      tool: 'CHECK_COMPLIANCE',
      quantity: totalPages,
      metadata: {
        "pages": totalPages,
        "docs": documents,
        "norms": norms,
      },
    });
  } catch (error) {
    console.error('Failed to record compliance usage', error);
  }
};

// Prefer Vite env variables (defined as VITE_*). Fallback to process.env for compatibility.
const API_KEY = import.meta.env.VITE_GEMINI_API_KEY || process.env.API_KEY;
if (!API_KEY) {
  throw new Error("Gemini API key missing. Set VITE_GEMINI_API_KEY in your Vite env or API_KEY in process.env.");
}

export interface ChatSource {
  title: string;
  uri: string;
}

export interface ChatResponse {
  text: string;
  sources: ChatSource[];
}

export interface DocumentSegment {
  id: string;
  text: string;
  issue?: ComplianceIssue; // Optional: only if this segment has a problem
}

export interface ComplianceIssue {
  title: string;
  status: 'NON_CONFORME' | 'BORDERLINE' | 'CONFORME' | 'CORRETTO' | 'IGNORATO';
  description: string;
  referenceNorm: string;
  suggestion: string;
}


class GeminiService {
  private ai: GoogleGenAI | null = null;

  constructor() {
    if (API_KEY) {
      this.ai = new GoogleGenAI({ apiKey: API_KEY });
    } else {
      console.warn("Gemini API Key is missing. AI features will not work.");
    }
  }

  public async generateDocument(
    type: string,
    company: Company | null,
    details: string,
    contextFiles: { mimeType: string; data: string }[] = []
  ): Promise<string> {
    if (!this.ai) {
      return "Errore: API Key mancante. Impossibile generare il documento.";
    }

    const modelId = 'gemini-2.5-flash';

    // Build text part with conditional company logic
    let companyInfo = "DATI SOCIETARI: Non specificati. Usa placeholder [NOME SOCIETA] o segui le istruzioni fornite.";

    if (company) {
      companyInfo = `
      DATI SOCIETARI:
      Nome: ${company.name}
      Tipo: ${company.type}
      Sede: ${company.address}
      P.IVA: ${company.vatNumber}
      Capitale Sociale: €${company.capital}
      Amministratori: ${company.officers.map(o => `${o.name} (${o.role})`).join(', ')}
      Soci: ${company.shareholders.map(s => `${s.name} (${s.quotaPercentage}%)`).join(', ')}
      ${company.letterheadInfo ? `\nTESTO CARTA INTESTATA:\n${company.letterheadInfo}\n` : ''}
      ${company.letterheadFile ? `\nNOTA: Ho allegato il file della carta intestata della società. Usa lo stile o le informazioni visive se pertinenti per formattare il documento.` : ''}
        `;
    }

    const textPrompt = `
      Agisci come un esperto avvocato societario italiano.
      Devi redigere un documento ${type ? `del tipo: "${type}"` : 'basato sulle istruzioni fornite'}.
      
      ${companyInfo}

      ISTRUZIONI SPECIFICHE / DETTAGLI:
      ${details}

      ${contextFiles.length > 0 ? 'NOTA: Ho allegato dei file di contesto (contratti, bozze). Usa il contenuto di questi file per redigere il documento richiesto.' : ''}

      Genera il documento usando formattazione Markdown (grassetto, elenchi puntati, titoli) per renderlo professionale e leggibile.
      Usa un linguaggio legale formale e preciso.
      Se i dati societari non sono presenti, usa dei placeholder chiari tipo [INSERIRE ...].
    `;

    // Construct parts (Text + Files + Letterhead)
    const parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> = [{ text: textPrompt }];

    // Helper to ensure valid MIME type
    const getSafeMimeType = (mimeType: string | undefined) => {
      return mimeType && mimeType.trim() !== '' ? mimeType : 'application/pdf';
    };

    // Add Context Files
    contextFiles.forEach(file => {
      if (file.data) {
        parts.push({
          inlineData: {
            mimeType: getSafeMimeType(file.mimeType),
            data: file.data
          }
        });
      }
    });

    // Add Letterhead File if exists and company is selected, and has valid base64 data
    if (company && company.letterheadFile && typeof company.letterheadFile === 'object' && 'data' in company.letterheadFile) {
      type LocalLetterhead = { data?: string; mimeType?: string; name?: string };
      const lf = company.letterheadFile as LocalLetterhead;
      if (lf.data && typeof lf.data === 'string') {
        parts.push({
          inlineData: {
            mimeType: getSafeMimeType(lf.mimeType),
            data: lf.data
          }
        });
      }
    }

    console.log('Generating document with parts:', parts);
    try {
      const response: GenerateContentResponse = await this.ai.models.generateContent({
        model: modelId,
        contents: { parts },
      });
      return response.text || "Nessun testo generato.";
    } catch (error) {
      console.error("Gemini API Error:", error);
      return `Errore nella generazione del documento: ${error instanceof Error ? error.message : 'Errore sconosciuto'}`;
    }
  }

  public async chatWithLegalAssistant(query: string, contextData: string): Promise<string> {
    if (!this.ai) return "Servizio AI non disponibile (API Key mancante).";

    const modelId = 'gemini-2.5-flash';

    const today = new Date().toLocaleDateString('it-IT', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    const systemInstruction = `
      Sei "LegalBot", un assistente virtuale per la segreteria societaria di uno studio legale.
      OGGI È: ${today}.
      Hai accesso ai dati dei clienti dello studio (forniti nel contesto).
      Rispondi alle domande in modo professionale, preciso e conciso.
      Se la domanda riguarda scadenze o dati societari, usa i dati forniti.
      Se ti chiedono "quali scadenze ci sono oggi o questa settimana", usa la data odierna (${today}) come riferimento per i calcoli.
    `;

    const prompt = `
      CONTESTO DATI (JSON):
      ${contextData}

      DOMANDA UTENTE:
      ${query}
    `;

    try {
      const response = await this.ai.models.generateContent({
        model: modelId,
        contents: prompt,
        config: {
          systemInstruction: systemInstruction
        }
      });

      // Registra l'uso del assistente legale
      api.post('/usage/manual/', {
        tool: 'SEGRETERIA_SOCIETARIA',
        subTool: 'ASSISTENTE_LEGALE',
        quantity: 0.5, // 2 interazioni = 1 uso
      });

      return response.text || "Non ho capito la domanda.";
    } catch (error) {
      console.error("Gemini Chat Error:", error);
      return "Si è verificato un errore di comunicazione con l'assistente.";
    }
  }
}

// MCP Server Configuration
const MCP_CONFIG = {
  label: "checkc-compliance-jurix",
  url: "https://mcp-server-check-compliance-latest.onrender.com/sse",
  auth: "none"
};

export const analyzeCompliance = async (
  files: ComplianceFile[],
  norms: string[]
): Promise<DocumentSegment[]> => {
  try {
    const ai = new GoogleGenAI({ apiKey: API_KEY });
    const modelId = 'gemini-2.5-flash';

    // -------------------------------------------------------------
    // MCP / Custom Database Logic
    // -------------------------------------------------------------
    let mcpContextInstruction = "";

    if (norms.includes("Database customizzato")) {
      console.log(`Connecting to Custom MCP Database [${MCP_CONFIG.label}] at ${MCP_CONFIG.url}...`);

      mcpContextInstruction = `
        IMPORTANTE: L'utente ha selezionato un database personalizzato "${MCP_CONFIG.label}".
        Devi verificare la conformità rispetto alle policy interne tipicamente ospitate su: ${MCP_CONFIG.url}.
        Simula le seguenti policy interne rigorose:
        1. Data Retention (max 5 anni).
        2. Foro Competente (solo Milano).
        3. Limite Responsabilità Fornitori (max 100% valore contratto).
        Segnala ogni violazione di queste regole.
        `;
    }

    // Updated Prompt to enforce Italian language
    const prompt = `
      Agisci come un Senior Compliance Officer.
      Obiettivo: Ricostruire il testo del documento fornito in un array JSON di "segmenti" (paragrafi/clausole) e analizzarne la conformità.
      
      ${mcpContextInstruction}

      Per OGNI segmento:
      1. 'text': Il contenuto testuale del paragrafo (mantieni lingua originale del testo).
      2. 'issue': Analizza se questo testo viola le seguenti normative: ${norms.join(', ')}. 
         Se valido/conforme, 'issue' è null. 
         Se invalido/rischioso, fornisci un oggetto con:
         - 'title': Titolo breve del problema (IN ITALIANO, es. "Mancata Data Retention").
         - 'status': "NON_CONFORME" (Critico) o "BORDERLINE" (Avviso).
         - 'description': Spiegazione del perché è un problema (IN ITALIANO).
         - 'referenceNorm': Riferimento normativo violato.
         - 'suggestion': Riscrittura del testo per renderlo conforme (IN ITALIANO).

      Assicurati che l'output copra l'INTERO contenuto del documento in sequenza.
      IMPORTANTE: TUTTI i campi di commento (description, suggestion, title) DEVONO ESSERE IN ITALIANO.
    `;

    type ContentPart = { text: string } | { inlineData: { mimeType: string; data: string } };
    const parts: ContentPart[] = [{ text: prompt }];
    files.forEach(file => {
      parts.push({
        inlineData: {
          mimeType: file.mimeType,
          data: file.data
        }
      });
    });

    const response = await ai.models.generateContent({
      model: modelId,
      contents: { parts },
      config: {
        responseMimeType: "application/json",
      },
    });

    const documentMetrics = await Promise.all(files.map((file) => countPdfPages(file)));
    const totalPages = documentMetrics.reduce((sum, metric) => sum + metric.pages, 0);
    await recordComplianceUsage(totalPages, documentMetrics, norms);

    if (response.text) {
      const rawData: unknown = JSON.parse(response.text);

      // Normalize to array of items with expected shape
      type DocumentSegmentInput = {
        text: string;
        issue?: Partial<ComplianceIssue> | null;
      };

      const segmentsArray: DocumentSegmentInput[] = Array.isArray(rawData)
        ? rawData as DocumentSegmentInput[]
        : ((rawData as { segments?: DocumentSegmentInput[] }).segments ?? []);

      return segmentsArray.map((item: DocumentSegmentInput, index: number) => ({
        id: `seg-${index}`,
        text: item.text,
        issue: item.issue ? {
          title: item.issue.title ?? '',
          status: (item.issue.status as ComplianceIssue['status']) ?? 'BORDERLINE',
          description: item.issue.description ?? '',
          referenceNorm: item.issue.referenceNorm ?? '',
          suggestion: item.issue.suggestion ?? ''
        } : undefined
      }));
    }
    return [];

  } catch (error) {
    console.error("Gemini Compliance Error:", error);
    // Fallback error
    return [
      {
        id: 'err-1',
        text: "Errore durante l'analisi del documento. Impossibile recuperare il testo.",
        issue: {
          title: 'Analisi Fallita',
          status: 'BORDERLINE',
          description: 'Impossibile completare l\'analisi automatica. Riprova.',
          referenceNorm: 'System',
          suggestion: ''
        }
      }
    ];
  }
};

export interface GeminiChatMessage {
  role: 'user' | 'ai';
  content: string;
}

export interface GeminiAttachment {
  mimeType: string;
  data: string;
}

export const generateGeminiResponse = async (
  prompt: string,
  modelId: string,
  history: GeminiChatMessage[] = [],
  attachments: GeminiAttachment[] = []
): Promise<string> => {
  const client = new GoogleGenAI({ apiKey: API_KEY });
  if (!client) return "Error: API Key missing.";

  try {
    // Mapping our internal ID to the actual API model ID
    // Note: The prompt requested "Gemini 3 Pro Preview"
    const apiModelName = modelId === 'gemini-3-pro-preview'
      ? 'gemini-3-pro-preview'
      : 'gemini-3-flash-preview'; // Fallback

    type GeminiContentPart = {
      text?: string;
      inlineData?: {
        mimeType: string;
        data: string;
      };
    };

    const conversation = history
      .filter(msg => Boolean(msg.content?.trim()))
      .slice(-10)
      .map(msg => ({
        role: msg.role === 'user' ? 'user' : 'model',
        parts: [{ text: msg.content } as GeminiContentPart]
      }));

    const attachmentParts = attachments
      .filter(att => att?.data)
      .map(att => ({
        inlineData: {
          mimeType: att.mimeType || 'application/octet-stream',
          data: att.data
        }
      } as GeminiContentPart));

    conversation.push({
      role: 'user',
      parts: [...attachmentParts, { text: prompt } as GeminiContentPart]
    });

    const response = await client.models.generateContent({
      model: apiModelName,
      contents: conversation,
    });

    api.post('/usage/manual/', {
      tool: 'CHAT_ASSISTANT',
      subTool: 'GEMINI_3_PRO_PREVIEW',
      quantity: 0.5, // 2 interazioni = 1 uso
    });

    return response.text || "No response text generated.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "Mi dispiace, si è verificato un errore durante la comunicazione con Gemini.";
  }
};

export const geminiService = new GeminiService();
