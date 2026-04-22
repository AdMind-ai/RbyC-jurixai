import { api } from "../api/api";
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

export const analyzeCompliance = async (
  files: ComplianceFile[],
  norms: string[]
): Promise<DocumentSegment[]> => {
  try {
    const response = await api.post("/openai/check-compliance/analyze/", {
      files,
      norms,
    });

    const documentMetrics = await Promise.all(files.map((file) => countPdfPages(file)));
    const totalPages = documentMetrics.reduce((sum, metric) => sum + metric.pages, 0);
    await recordComplianceUsage(totalPages, documentMetrics, norms);

    if (response.data) {
      const rawData: unknown = response.data;
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
    console.error("OpenAI Compliance Error:", error);
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
