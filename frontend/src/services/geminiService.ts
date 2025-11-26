
import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { Company } from '../types/types';

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

interface GroundingChunk {
  web?: {
    title?: string;
    uri?: string;
  };
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

    // Add Letterhead File if exists and company is selected, and has valid data
    if (
      company &&
      company.letterheadFile &&
      company.letterheadFile.data
    ) {
      parts.push({
        inlineData: {
          mimeType: getSafeMimeType(company.letterheadFile.mimeType),
          data: company.letterheadFile.data
        }
      });
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
      return response.text || "Non ho capito la domanda.";
    } catch (error) {
      console.error("Gemini Chat Error:", error);
      return "Si è verificato un errore di comunicazione con l'assistente.";
    }
  }

  /**
   * General Chat with Gemini 3 (Pro Preview), Google Search, and File support.
   */
  public async generalChatWithSearch(
    message: string,
    files: { mimeType: string; data: string }[] = [],
    history: { role: 'user' | 'model', text: string }[] = []
  ): Promise<ChatResponse> {
    if (!this.ai) return { text: "Servizio AI non disponibile (API Key mancante).", sources: [] };

    // Use Gemini 3 Pro Preview for complex tasks and reasoning
    const modelId = 'gemini-3-pro-preview';

    const parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> = [];

    // Add files first
    files.forEach(file => {
      parts.push({
        inlineData: {
          mimeType: file.mimeType,
          data: file.data
        }
      });
    });

    // Add text message
    parts.push({ text: message });

    // Construct history parts for context (simplified for single-turn API structure, 
    // ideally use chats.create for proper history, but mixing search tools + history manually here for control)
    // For this implementation, we will rely on the system instruction + current prompt for simplicity in the single call,
    // or we could prepend history to the prompt. Let's prepend history to the text prompt for context.
    let fullPrompt = message;
    if (history.length > 0) {
      const historyText = history.map(h => `${h.role.toUpperCase()}: ${h.text}`).join('\n');
      fullPrompt = `CONTESTO CONVERSAZIONE PRECEDENTE:\n${historyText}\n\nNUOVA RICHIESTA UTENTE:\n${message}`;
      // Update the text part
      parts[parts.length - 1] = { text: fullPrompt };
    }

    try {
      const response = await this.ai.models.generateContent({
        model: modelId,
        contents: { parts },
        config: {
          tools: [{ googleSearch: {} }], // Enable Google Search Grounding
          systemInstruction: "Sei un assistente legale avanzato. Usa la Ricerca Google per trovare informazioni recenti, sentenze, o normative aggiornate se necessario. Rispondi in italiano professionale. Se usi informazioni dal web, cita le fonti."
        }
      });

      // Extract grounding metadata (sources)
      const sources: ChatSource[] = [];
      const groundingChunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks;

      if (groundingChunks) {
        groundingChunks.forEach((chunk: GroundingChunk) => {
          if (chunk.web && typeof chunk.web.uri === 'string') {
            sources.push({
              title: chunk.web.title || 'Fonte Web',
              uri: chunk.web.uri
            });
          }
        });
      }

      return {
        text: response.text || "Non è stata generata alcuna risposta.",
        sources: sources
      };

    } catch (error) {
      console.error("Gemini General Chat Error:", error);
      return {
        text: "Si è verificato un errore durante l'elaborazione della richiesta. Riprova più tardi.",
        sources: []
      };
    }
  }
}

export const geminiService = new GeminiService();
