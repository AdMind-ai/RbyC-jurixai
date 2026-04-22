import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { Company } from "../types/types";

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY || process.env.API_KEY;
if (!API_KEY) {
  console.warn("Gemini API key missing. Gemini-only features will not work.");
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

export const geminiService = new GeminiService();
