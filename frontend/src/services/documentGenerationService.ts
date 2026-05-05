import { fetchWithAuth } from "../api/fetchWithAuth";
import { Company } from "../types/types";

class DocumentGenerationService {
  public async generateDocument(
    type: string,
    company: Company | null,
    details: string,
    contextFiles: { name?: string; mimeType: string; data: string }[] = []
  ): Promise<string> {
    try {
      const response = await fetchWithAuth("/openai/segreteria/document-generator/", {
        method: "POST",
        body: JSON.stringify({
          company_id: company?.id ?? null,
          doc_type: type,
          details,
          context_files: contextFiles,
        }),
      });

      if (!response || !response.ok) {
        const errorBody = response ? await response.text() : "Unknown error";
        throw new Error(errorBody || "OpenAI request failed");
      }

      const payload = await response.json();
      return payload.generated_content || "Nessun testo generato.";
    } catch (error) {
      console.error("OpenAI document generation error:", error);
      return `Errore nella generazione del documento: ${
        error instanceof Error ? error.message : "Errore sconosciuto"
      }`;
    }
  }
}

export const documentGenerationService = new DocumentGenerationService();
