import { Box, Button, Typography, CircularProgress } from '@mui/material'
import { useRef, useState, useEffect } from 'react'
import UploadableTextArea from '../upload-components/UploadableTextArea'
import { api } from '../../api/api'
import { toast } from 'react-toastify'

interface Document {
  id: number;
  name: string;
  type: string;
  extractContent?: string;      
}

// Simulação "resultado da análise" para a segunda caixa ("mockup result")
const MOCK_ANALYSIS = {
  result: '60% positivo',
  links: [
    { url: "https://www.sec.gov/files/rules/other/33-10884.pdf", clause: "3.4.1, 5.1" },
    { url: "https://www.sec.gov/files/rules/other/33-10884.pdf", clause: "3.4.1, 5.1" },
    { url: "https://www.sec.gov/files/rules/other/33-10884.pdf", clause: "3.4.1, 5.1" },
    { url: "https://www.sec.gov/files/rules/other/33-10884.pdf", clause: "3.4.1, 5.1" },
  ]
};


const DocCheck = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [isFileExtracted, setIsFileExtracted] = useState(false);
  const [documentsExtracted, setDocumentsExtracted] = useState<Document[]>([]);
  const [isAnalyzed, setIsAnalyzed] = useState(false);
  const isButtonEnabled = files.length > 0;

  // Seletor de trecho
  const [selections, setSelections] = useState<{ start: number; end: number; text: string }[]>([]);
  
  // refs
  const [leftHoveredIdx, setLeftHoveredIdx] = useState<number | null>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const resultRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (
      leftHoveredIdx !== null &&
      resultRefs.current[leftHoveredIdx] 
    ) {
      resultRefs.current[leftHoveredIdx]?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",     
      });
    }
  }, [leftHoveredIdx]);

  // File Delete 
  // const handleDeleteDocument = (id: number) => {
  //   setDocumentsExtracted((prevDocs) => prevDocs.filter((doc) => doc.id !== id));
  //   if (documentsExtracted.length === 0) {
  //     setIsFileExtracted(false);
  //   }
  // };

  // File Upload
  const handleFileUpload = (file: File | File[]) => {
    setFiles(prevFiles => [
      ...prevFiles,
      ...(Array.isArray(file) ? file : [file])
    ]);
  };

  // File Extension
  const getFileExtension = (filename: string) => {
    return filename.substring(filename.lastIndexOf('.') + 1, filename.length);
  };

  const handleNewExtract = () => {
    setSelections([]);
    setIsAnalyzed(false);
    setIsFileExtracted(false);
    setDocumentsExtracted([]);
    setFiles([]);
  };

  const handleExtract = async () => {
    setIsLoading(true);
    try {
      const extractRequests = files.map(file => {
        const formData = new FormData();
        formData.append('file', file);

        return api.post('/extract-content/file/', formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
      });

      const responses = await Promise.all(extractRequests);

      const extractedDocuments: Document[] = responses.map((res, idx) => {
        const fileName = res.data.document || files[idx].name;
        const fileExtension = getFileExtension(fileName);

        return {
          id: Date.now() + idx,
          name: fileName,
          type: fileExtension,
          extractContent: res.data.content, 
        };
      });

      setDocumentsExtracted(prevDocs => [...prevDocs, ...extractedDocuments]);
      setIsFileExtracted(true);
      setFiles([]);
      setIsLoading(false);

    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      toast.error(`Error extracting document: ${msg}`);
      setIsLoading(false);
    }
  };

  // === Seleção de texto ===
  function handleMouseUp() {
    if (isAnalyzed || !textRef.current) return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return;
    const anchorNode = sel.anchorNode;
    // const focusNode = sel.focusNode;

    // Só aceita seleção dentro do texto extraído
    if (anchorNode && textRef.current.contains(anchorNode)) {
      let idxStart = getCharIndexInText(textRef.current, sel.anchorNode, sel.anchorOffset);
      let idxEnd = getCharIndexInText(textRef.current, sel.focusNode, sel.focusOffset);
      if (idxStart > idxEnd) [idxStart, idxEnd] = [idxEnd, idxStart];
      if (idxStart !== idxEnd) {
        // Verifica duplicidade ou overlap (remove trecho se já está, senão adiciona)
        const existsIdx = selections.findIndex(s => s.start === idxStart && s.end === idxEnd);
        if (existsIdx !== -1) {
          setSelections(prev => prev.filter((_, i) => i !== existsIdx));
        } else {
          setSelections(prev => [...prev, {
            start: idxStart,
            end: idxEnd,
            text: documentsExtracted[0]?.extractContent?.slice(idxStart, idxEnd) ?? ""
          }]);
        }
      }
    }
    sel.removeAllRanges();
  }

  // Função para transformar node/offset em índice absoluto no texto
  function getCharIndexInText(container: HTMLElement, node: Node | null, offset: number) {
    if (!node) return 0;
    let count = 0;
    let found = false;
    function traverse(curr: Node) {
      if (found) return;
      if (curr === node) {
        count += offset;
        found = true;
        return;
      }
      if (curr.nodeType === 3) {
        count += (curr.textContent || "").length;
      } else {
        for (let child = curr.firstChild; child && !found; child = child.nextSibling) {
          traverse(child);
        }
      }
    }
    traverse(container);
    return count;
  }

  // Remover seleção
  function handleRemoveSelection(idx: number) {
    if (isAnalyzed) return;
    setSelections(prev => prev.filter((_, i) => i !== idx));
  }

  // Renderiza com highlights
  function renderHighlightedText(text: string) {
    if (!text) return null;
    const elements: React.ReactNode[] = [];
    let pointer = 0;
    const sorted = [...selections].sort((a, b) => a.start - b.start);

    sorted.forEach((s, idx) => {
      if (pointer < s.start) {
        elements.push(<span key={pointer}>{text.slice(pointer, s.start)}</span>);
      }
      elements.push(
        <span
          key={s.start + '-' + s.end}
          style={{
            background:
              isAnalyzed
                ? leftHoveredIdx === idx
                  ? "#eafaf3"
                  : "transparent"
                : "#f9ea97",
            color: isAnalyzed ? "#23ad5c" : "#222",
            fontWeight: isAnalyzed ? 500 : undefined,
            borderRadius: 4,
            cursor: isAnalyzed ? "pointer" : "pointer",
            padding: "0 2px",
            transition: 'background 0.12s',
            border: isAnalyzed && leftHoveredIdx === idx ? "1.2px solid #23ad5c" : "none"
          }}
          onClick={() => !isAnalyzed && handleRemoveSelection(idx)}
          onMouseEnter={() => { if(isAnalyzed) setLeftHoveredIdx(idx); }}
          onMouseLeave={() => { if(isAnalyzed) setLeftHoveredIdx(null); }}
        >
          {text.slice(s.start, s.end)}
        </span>
      );
      pointer = s.end;
    });
    if (pointer < text.length) {
      elements.push(<span key={pointer}>{text.slice(pointer)}</span>);
    }
    return elements;
  }

  const selectedCharCount = selections.reduce((acc, s) => acc + (s.end - s.start), 0);
  const extractDoc = documentsExtracted[0]; // Usando o primeiro

  return (
    <Box
      sx={{
        height:'100%',
        width:'100%'
      }}
    >
      {!isFileExtracted ? (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems:'center',
            justifyContent:'center',
            height:'100%',
          }}
        >
          <UploadableTextArea onFileUpload={handleFileUpload} documentPlaceHolder='Carica un file o trascinalo qui' />
          <Button
            variant="contained"
            color="primary"
            disabled={!isButtonEnabled || isLoading}
            onClick={handleExtract}
            sx={{ width: 'calc(9.5vw)', mt: 2 }}
          >
            {isLoading ? <CircularProgress size={24} color="inherit" /> : 'Avvia'}
          </Button>
        </Box>
      ):(
        <Box sx={{ display: "flex", flexDirection: "row", width: "100%", minHeight: 400, gap: 1, 
          // bgcolor:'blue' 
          }}
        >
          {/* LEFT BOX */}
          <Box sx={{ width: "60%", display: "flex", flexDirection: "column", gap: 1, 
            // bgcolor: 'red' 
            }}
          >
            <Typography variant="caption" sx={{ color: "#888", ml: .3, mb: 0 }}>Documento caricato:</Typography>
            {extractDoc && (
              <Typography variant="subtitle2" fontWeight={700} sx={{ ml: .3 }}>
                {extractDoc.name}
              </Typography>
            )}
            <Box
              ref={textRef}
              onMouseUp={isFileExtracted && !isAnalyzed ? handleMouseUp : undefined}
              sx={{
                mt: 1,
                background: "#fff",
                border: "1px solid #ededed",
                minHeight: 400,
                height: 400,
                maxHeight: 400,
                overflowY: "auto",
                borderRadius: 2.5,
                fontSize: 13,
                color: "#222",
                lineHeight: 1.45,
                p: 2,
                fontFamily: 'monospace',
                boxSizing: "border-box",
                cursor: isAnalyzed ? undefined : "text",
                userSelect: isAnalyzed ? "none" : "text",
                transition: "border .1s"
              }}
            >
              {extractDoc ? renderHighlightedText(extractDoc.extractContent || "") : (
                <Typography color="text.secondary" fontStyle="italic">Nenhum conteúdo extraído.</Typography>
              )}
            </Box>

            {isFileExtracted && (
              <Box sx={{ mt:1, display: "flex", alignItems: "flex-end", justifyContent:'space-between', gap: 1 }}>
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                  }}
                >
                  <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5, ml: .3 }}>
                    Seleziona il testo che desideri analizzare
                  </Typography>
                  <Typography variant="caption" sx={{ color: "#777", ml: .3 }}>
                    Testo selezionato: {selectedCharCount}/50000000000000
                  </Typography>
                </Box>
                <Box
                  sx={{ 
                    display:'flex',
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap:1
                  }}
                >
                  <Button
                    variant="outlined"
                    color="primary"
                    onClick={handleNewExtract}
                    sx={{ width: 165, alignSelf: 'flex-start' }}
                  >
                    Nuovo documento
                  </Button>
                  <Button
                    sx={{ width: 125 }}
                    variant="contained"
                    color="secondary"
                    disabled={selectedCharCount === 0 || isAnalyzed}
                    onClick={() => setIsAnalyzed(true)}
                  >
                    Avvia analisi
                  </Button>
                </Box>
              </Box>
            )}

          </Box>

          {/* RIGHT BOX */}
          <Box sx={{ width: "40%", display: "flex", flexDirection: "column", height:'100%' }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 2, mt: 3.6, ml:.3 }}>
              Analisi della selezione
            </Typography>
            <Box sx={{
              border: "1px solid #ededed",
              minHeight: 470,
              height: 470,
              maxHeight: 470,
              overflowY: "auto",
              borderRadius: 2.5,
              background: "#fff",
              fontSize: 13,
              color: "#222",
              lineHeight: 1.45,
              p: 2
            }}>
              {/* MOCKED RESULT */}
              {isAnalyzed ? (
                <Box>
                  <Typography fontWeight={700} fontSize={15} sx={{ mb: 1 }}>
                    Esito: <span style={{ color: "#23ad5c" }}>{MOCK_ANALYSIS.result}</span>
                  </Typography>
                  {selections.length === 0 && <Typography variant="body2" color="text.secondary">Nessuna selezione</Typography>}
                  {selections.map((_, idx) => (
                    <Box
                      ref={el => { resultRefs.current[idx] = el as HTMLDivElement | null; }}
                      key={idx}
                      sx={{
                        borderRadius: 2,
                        mb: 1,
                        p: leftHoveredIdx === idx ? 1.2 : 0.4,
                        background: leftHoveredIdx === idx ? "#ecf6ff" : "transparent"
                      }}
                    >
                      <Typography variant="caption" sx={{ color: "#888" }}>Ref.:</Typography>{" "}
                      <a
                        href={MOCK_ANALYSIS.links[idx % MOCK_ANALYSIS.links.length].url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: leftHoveredIdx === idx ? "#1976d2" : "#4e5fc3",
                          fontSize: 13,
                          textDecoration: "underline",
                          fontWeight: 500,
                          cursor: "pointer"
                        }}
                      >
                        US.compliance_residents.PDF
                      </a>
                      <Typography variant="caption" sx={{ color: "#888", display: "block" }}>
                        Clausole: {MOCK_ANALYSIS.links[idx % MOCK_ANALYSIS.links.length].clause}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              ) : null}
            </Box>
          </Box>
        </Box>
      )}
    </Box>
  )
}

export default DocCheck