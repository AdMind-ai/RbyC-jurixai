import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { api } from "../api/api";
import { Company } from "../types/types";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf";
import workerSrc from "pdfjs-dist/legacy/build/pdf.worker?url";

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
  Boolean(mimeType && mimeType.toLowerCase().includes("pdf"));

const base64ToUint8Array = (input: string): Uint8Array => {
  const cleaned = (input || "").split(",").pop() ?? "";
  const binary = atob(cleaned);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
};

const countPdfPages = async (file: ComplianceFile): Promise<ComplianceDocumentMetric> => {
  if (!isPdfMimeType(file.mimeType) || !file.data) {
    return { name: file.name, mimeType: file.mimeType, pages: 0 };
  }
  try {
    const loadingTask = pdfjsLib.getDocument({ data: base64ToUint8Array(file.data) });
    const pdf = await loadingTask.promise;
    const pages = pdf.numPages || 0;
    pdf.destroy();
    return { name: file.name, mimeType: file.mimeType, pages };
  } catch (error) {
    console.warn("Failed to count pages for file", file.name, error);
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
    await api.post("/usage/manual/", {
      tool: "CHECK_COMPLIANCE",
      quantity: 1,
      metadata: {
        pages: totalPages,
        docs: documents,
        norms,
      },
    });
  } catch (error) {
    console.error("Failed to record compliance usage", error);
  }
};

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY || process.env.API_KEY;
if (!API_KEY) {
  throw new Error(
    "Gemini API key missing. Set VITE_GEMINI_API_KEY in your Vite env or API_KEY in process.env."
  );
}

export interface DocumentSegment {
  id: string;
  text: string;
  issue?: ComplianceIssue;
}

export interface ComplianceIssue {
  title: string;
  status: "NON_CONFORME" | "BORDERLINE" | "CONFORME" | "CORRETTO" | "IGNORATO";
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

    const modelId = "gemini-2.5-flash";
    let companyInfo =
      "DATI SOCIETARI: Non specificati. Usa placeholder [NOME SOCIETA] o segui le istruzioni fornite.";

    if (company) {
      companyInfo = `
      DATI SOCIETARI:
      Nome: ${company.name}
      Tipo: ${company.type}
      Sede: ${company.address}
      P.IVA: ${company.vatNumber}
      Capitale Sociale: EUR ${company.capital}
      Amministratori: ${company.officers.map((officer) => `${officer.name} (${officer.role})`).join(", ")}
      Soci: ${company.shareholders.map((shareholder) => `${shareholder.name} (${shareholder.quotaPercentage}%)`).join(", ")}
      ${company.letterheadInfo ? `\nTESTO CARTA INTESTATA:\n${company.letterheadInfo}\n` : ""}
      ${company.letterheadFile ? "\nNOTA: Ho allegato il file della carta intestata della societa. Usa lo stile o le informazioni visive se pertinenti per formattare il documento." : ""}
      `;
    }

    const textPrompt = `
      Agisci come un esperto avvocato societario italiano.
      Devi redigere un documento ${type ? `del tipo: "${type}"` : "basato sulle istruzioni fornite"}.

      ${companyInfo}

      ISTRUZIONI SPECIFICHE / DETTAGLI:
      ${details}

      ${contextFiles.length > 0 ? "NOTA: Ho allegato dei file di contesto (contratti, bozze). Usa il contenuto di questi file per redigere il documento richiesto." : ""}

      Genera il documento usando formattazione Markdown (grassetto, elenchi puntati, titoli) per renderlo professionale e leggibile.
      Usa un linguaggio legale formale e preciso.
      Se i dati societari non sono presenti, usa dei placeholder chiari tipo [INSERIRE ...].
    `;

    const parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> = [
      { text: textPrompt },
    ];
    const getSafeMimeType = (mimeType: string | undefined) =>
      mimeType && mimeType.trim() !== "" ? mimeType : "application/pdf";

    contextFiles.forEach((file) => {
      if (file.data) {
        parts.push({
          inlineData: {
            mimeType: getSafeMimeType(file.mimeType),
            data: file.data,
          },
        });
      }
    });

    if (
      company &&
      company.letterheadFile &&
      typeof company.letterheadFile === "object" &&
      "data" in company.letterheadFile
    ) {
      type LocalLetterhead = { data?: string; mimeType?: string; name?: string };
      const letterheadFile = company.letterheadFile as LocalLetterhead;
      if (letterheadFile.data && typeof letterheadFile.data === "string") {
        parts.push({
          inlineData: {
            mimeType: getSafeMimeType(letterheadFile.mimeType),
            data: letterheadFile.data,
          },
        });
      }
    }

    try {
      const response: GenerateContentResponse = await this.ai.models.generateContent({
        model: modelId,
        contents: { parts },
      });
      return response.text || "Nessun testo generato.";
    } catch (error) {
      console.error("Gemini API Error:", error);
      return `Errore nella generazione del documento: ${
        error instanceof Error ? error.message : "Errore sconosciuto"
      }`;
    }
  }
}

const MCP_CONFIG = {
  label: "checkc-compliance-jurix",
  url: "https://mcp-server-check-compliance-latest.onrender.com/sse",
  auth: "none",
};

export const geminiService = new GeminiService();

export const analyzeCompliance = async (
  files: ComplianceFile[],
  norms: string[]
): Promise<DocumentSegment[]> => {
  try {
    const ai = new GoogleGenAI({ apiKey: API_KEY });
    const modelId = "gemini-2.5-flash";

    let mcpContextInstruction = "";
    if (norms.includes("Database customizzato")) {
      mcpContextInstruction = `
        IMPORTANTE: L'utente ha selezionato un database personalizzato "${MCP_CONFIG.label}".
        Devi verificare la conformita rispetto alle policy interne tipicamente ospitate su: ${MCP_CONFIG.url}.
        Simula le seguenti policy interne rigorose:
        1. Data Retention (max 5 anni).
        2. Foro Competente (solo Milano).
        3. Limite Responsabilita Fornitori (max 100% valore contratto).
        Segnala ogni violazione di queste regole.
      `;
    }

    const prompt = `
      Agisci come un Senior Compliance Officer.
      Obiettivo: Ricostruire il testo del documento fornito in un array JSON di "segmenti" (paragrafi/clausole) e analizzarne la conformita.

      ${mcpContextInstruction}

      Per OGNI segmento:
      1. 'text': Il contenuto testuale del paragrafo (mantieni lingua originale del testo).
      2. 'issue': Analizza se questo testo viola le seguenti normative: ${norms.join(", ")}.
         Se valido/conforme, 'issue' e null.
         Se invalido/rischioso, fornisci un oggetto con:
         - 'title': Titolo breve del problema (IN ITALIANO, es. "Mancata Data Retention").
         - 'status': "NON_CONFORME" (Critico) o "BORDERLINE" (Avviso).
         - 'description': Spiegazione del perche e un problema (IN ITALIANO).
         - 'referenceNorm': Riferimento normativo violato.
         - 'suggestion': Riscrittura del testo per renderlo conforme (IN ITALIANO).

      Assicurati che l'output copra l'INTERO contenuto del documento in sequenza.
      IMPORTANTE: TUTTI i campi di commento (description, suggestion, title) DEVONO ESSERE IN ITALIANO.
    `;

    type ContentPart = { text: string } | { inlineData: { mimeType: string; data: string } };
    const parts: ContentPart[] = [{ text: prompt }];
    files.forEach((file) => {
      parts.push({
        inlineData: {
          mimeType: file.mimeType,
          data: file.data,
        },
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
      type DocumentSegmentInput = {
        text: string;
        issue?: Partial<ComplianceIssue> | null;
      };

      const segmentsArray: DocumentSegmentInput[] = Array.isArray(rawData)
        ? (rawData as DocumentSegmentInput[])
        : ((rawData as { segments?: DocumentSegmentInput[] }).segments ?? []);

      return segmentsArray.map((item, index) => ({
        id: `seg-${index}`,
        text: item.text,
        issue: item.issue
          ? {
              title: item.issue.title ?? "",
              status: (item.issue.status as ComplianceIssue["status"]) ?? "BORDERLINE",
              description: item.issue.description ?? "",
              referenceNorm: item.issue.referenceNorm ?? "",
              suggestion: item.issue.suggestion ?? "",
            }
          : undefined,
      }));
    }
    return [];
  } catch (error) {
    console.error("Gemini Compliance Error:", error);
    return [
      {
        id: "err-1",
        text: "Errore durante l'analisi del documento. Impossibile recuperare il testo.",
        issue: {
          title: "Analisi Fallita",
          status: "BORDERLINE",
          description: "Impossibile completare l'analisi automatica. Riprova.",
          referenceNorm: "System",
          suggestion: "",
        },
      },
    ];
  }
};
