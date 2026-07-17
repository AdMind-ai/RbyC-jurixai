import React, { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Download,
  File as FileIcon,
  FileArchive,
  FileCode,
  FileJson,
  FileSpreadsheet,
  FileText,
  FileType,
  FileUp,
  FolderOpen,
  MoreVertical,
  Presentation,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-react';

import {
  checkComplianceDocumentsService,
  ComplianceDocument,
} from '../services/checkComplianceDocumentsService';

const folderLabels: Record<string, string> = {
  'documents/regulatory/banca-ditalia/': "Banca d'Italia",
  'documents/regulatory/consob/': 'Consob',
  'documents/regulatory/eur-lex/': 'EUR-Lex',
  'documents/regulatory/normattiva-gazzetta/': 'Normattiva / Gazzetta',
  'documents/regulatory/esma/': 'ESMA',
  'documents/regulatory/eba/': 'EBA',
  'documents/regulatory/ivass/': 'IVASS',
  'documents/regulatory/assogestioni/': 'Assogestioni',
  'documents/regulatory/fonte-da-definire/': 'Fonte da definire',
};

const formatFileSize = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, index);
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
};

const formatDate = (value: string | null) => {
  if (!value) return '-';
  return new Date(value).toLocaleString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getFileIcon = (name: string) => {
  const extension = name.split('.').pop()?.toLowerCase();
  if (extension === 'pdf') return FileType;
  if (['xls', 'xlsx', 'csv', 'ods'].includes(extension || '')) return FileSpreadsheet;
  if (['doc', 'docx', 'txt', 'md', 'rtf', 'odt'].includes(extension || '')) return FileText;
  if (['ppt', 'pptx'].includes(extension || '')) return Presentation;
  if (['json'].includes(extension || '')) return FileJson;
  if (['html', 'xml'].includes(extension || '')) return FileCode;
  if (['zip', 'rar', '7z'].includes(extension || '')) return FileArchive;
  return FileIcon;
};

const getFileVisual = (name: string) => {
  const extension = name.split('.').pop()?.toLowerCase() || 'file';

  if (extension === 'pdf') {
    return { colorClass: 'bg-red-50 text-red-600 border-red-100' };
  }
  if (['xls', 'xlsx', 'csv', 'ods'].includes(extension)) {
    return { colorClass: 'bg-emerald-50 text-emerald-600 border-emerald-100' };
  }
  if (['doc', 'docx', 'odt'].includes(extension)) {
    return { colorClass: 'bg-blue-50 text-blue-600 border-blue-100' };
  }
  if (['ppt', 'pptx'].includes(extension)) {
    return { colorClass: 'bg-orange-50 text-orange-600 border-orange-100' };
  }
  if (['txt', 'md', 'rtf'].includes(extension)) {
    return { colorClass: 'bg-slate-100 text-slate-600 border-slate-200' };
  }
  if (extension === 'json') {
    return { colorClass: 'bg-amber-50 text-amber-600 border-amber-100' };
  }
  if (['html', 'xml'].includes(extension)) {
    return { colorClass: 'bg-violet-50 text-violet-600 border-violet-100' };
  }
  if (['zip', 'rar', '7z'].includes(extension)) {
    return { colorClass: 'bg-stone-100 text-stone-600 border-stone-200' };
  }

  return { colorClass: 'bg-gray-100 text-gray-600 border-gray-200' };
};

const FileTypeBadge: React.FC<{ name: string; compact?: boolean }> = ({ name, compact = false }) => {
  const Icon = getFileIcon(name);
  const visual = getFileVisual(name);

  return (
    <div
      className={`inline-flex shrink-0 items-center justify-center rounded-lg border ${visual.colorClass} ${
        compact ? 'h-8 w-8' : 'h-10 w-10'
      }`}
      title={name.split('.').pop()?.toUpperCase() || 'FILE'}
    >
      <Icon className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
    </div>
  );
};

const normalizeFolder = (folder: string) => {
  return folder.replace(/\/?$/, '/');
};

const getFolderLabel = (folder: string) => {
  const normalized = normalizeFolder(folder);
  const knownLabel = folderLabels[normalized];
  if (knownLabel) return knownLabel;

  const parts = normalized.split('/').filter(Boolean);
  return parts[parts.length - 1] || normalized;
};

const slugifyFolderName = (value: string) => {
  return value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
};

const CheckComplianceDocuments: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderMenuRef = useRef<HTMLDivElement | null>(null);
  const [documents, setDocuments] = useState<ComplianceDocument[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string>('documents/regulatory/');
  const [folderFilter, setFolderFilter] = useState<string>('all');
  const [isFolderFilterOpen, setIsFolderFilterOpen] = useState(false);
  const [useCustomFolder, setUseCustomFolder] = useState(false);
  const [customFolderName, setCustomFolderName] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [documentToDelete, setDocumentToDelete] = useState<ComplianceDocument | null>(null);
  const [deleteConfirmationStep, setDeleteConfirmationStep] = useState(1);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState('');
  const [openActionKey, setOpenActionKey] = useState<string | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const active = await checkComplianceDocumentsService.listDocuments();
      setDocuments(active.documents);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore nel caricamento dei documenti.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!isFolderFilterOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (
        folderMenuRef.current
        && !folderMenuRef.current.contains(event.target as Node)
      ) {
        setIsFolderFilterOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [isFolderFilterOpen]);

  const visibleDocuments = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return documents.filter((document) => {
      const folderMatches =
        folderFilter === 'all'
        || document.key.startsWith(folderFilter);
      const queryMatches =
        !normalizedQuery
        || `${document.name} ${document.key} ${document.folder}`.toLowerCase().includes(normalizedQuery);

      return folderMatches && queryMatches;
    });
  }, [documents, folderFilter, query]);

  const availableFolders = useMemo(() => {
    const folders = new Set<string>();
    documents.forEach((document) => {
      if (document.folder) {
        folders.add(normalizeFolder(document.folder));
      }
    });

    if (folders.size === 0) {
      folders.add('documents/regulatory/');
    }

    return Array.from(folders).sort((a, b) =>
      getFolderLabel(a).localeCompare(getFolderLabel(b))
    );
  }, [documents]);

  useEffect(() => {
    if (!availableFolders.includes(selectedFolder)) {
      setSelectedFolder(availableFolders[0] || 'documents/regulatory/');
    }
  }, [availableFolders, selectedFolder]);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFiles(Array.from(event.target.files ?? []));
  };

  const handleRemoveSelectedFile = (indexToRemove: number) => {
    setSelectedFiles((current) =>
      current.filter((_, index) => index !== indexToRemove)
    );
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    const customFolderSlug = slugifyFolderName(customFolderName);
    const uploadPrefix = useCustomFolder
      ? `documents/regulatory/${customFolderSlug}/`
      : selectedFolder;

    if (useCustomFolder && !customFolderSlug) {
      setError('Inserisci un nome valido per la nuova cartella.');
      return;
    }

    setActionLoading('upload');
    setError(null);
    try {
      await checkComplianceDocumentsService.uploadDocuments(selectedFiles, uploadPrefix);
      setSelectedFiles([]);
      setCustomFolderName('');
      setUseCustomFolder(false);
      setSelectedFolder(uploadPrefix);
      setIsUploadModalOpen(false);
      await loadDocuments();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore durante upload del documento.';
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  const closeDeleteModal = () => {
    setDocumentToDelete(null);
    setDeleteConfirmationStep(1);
    setDeleteConfirmationText('');
  };

  const handleDownload = async (document: ComplianceDocument) => {
    setActionLoading(`download:${document.key}`);
    setOpenActionKey(null);
    setError(null);
    try {
      const { url } = await checkComplianceDocumentsService.getDownloadUrl(document.key);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore durante il download del documento.';
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  const openDeleteModal = (document: ComplianceDocument) => {
    setOpenActionKey(null);
    setDocumentToDelete(document);
    setDeleteConfirmationStep(1);
    setDeleteConfirmationText('');
  };

  const handlePermanentDelete = async () => {
    if (!documentToDelete) return;
    const document = documentToDelete;
    setActionLoading(document.key);
    setError(null);
    try {
      await checkComplianceDocumentsService.permanentlyDeleteDocument(document.key);
      closeDeleteModal();
      await loadDocuments();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore durante eliminazione del documento.';
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="h-full w-full overflow-y-auto bg-slate-50 p-8 lg:p-12">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#172554]">Documenti Check Compliance</h1>
            <p className="mt-2 text-sm text-slate-500">
              Gestione dei documenti disponibili in S3 per la base normativa.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1F3A8B] px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#172554]"
            >
              <FileUp className="h-4 w-4" />
              Upload documento
            </button>
            <button
              onClick={loadDocuments}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-[#172554] shadow-sm transition-colors hover:bg-slate-100 disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Aggiorna
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex min-w-0 shrink-0 gap-3 lg:items-center">
                <div className="rounded-lg bg-[#1F3A8B] px-4 py-2 text-sm font-semibold text-white">
                  Documenti ({documents.length})
                </div>

                <label className="sr-only" htmlFor="folder-filter-button">
                  Filtra per cartella
                </label>
                <div ref={folderMenuRef} className="relative w-[300px] max-w-[calc(100vw-2rem)] sm:w-[340px]">
                  <button
                    id="folder-filter-button"
                    type="button"
                    onClick={() => setIsFolderFilterOpen((current) => !current)}
                    className="flex w-full items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm font-medium text-slate-700 outline-none transition-colors hover:bg-slate-50 focus:border-[#1F3A8B]"
                    title={folderFilter === 'all' ? 'Tutte le cartelle' : getFolderLabel(folderFilter)}
                  >
                    <span className="min-w-0 flex-1 truncate">
                      {folderFilter === 'all' ? 'Tutte le cartelle' : getFolderLabel(folderFilter)}
                    </span>
                    <span className="shrink-0 text-slate-400">⌄</span>
                  </button>

                  {isFolderFilterOpen && (
                    <div className="absolute left-0 top-[calc(100%+6px)] z-40 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                      <button
                        type="button"
                        onClick={() => {
                          setFolderFilter('all');
                          setIsFolderFilterOpen(false);
                        }}
                        className={`flex w-full px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50 ${
                          folderFilter === 'all'
                            ? 'font-semibold text-[#1F3A8B]'
                            : 'font-medium text-slate-700'
                        }`}
                        title="Tutte le cartelle"
                      >
                        <span className="truncate">Tutte le cartelle</span>
                      </button>
                      {availableFolders.map((folder) => (
                        <button
                          key={folder}
                          type="button"
                          onClick={() => {
                            setFolderFilter(folder);
                            setIsFolderFilterOpen(false);
                          }}
                          className={`flex w-full px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50 ${
                            folderFilter === folder
                              ? 'font-semibold text-[#1F3A8B]'
                              : 'font-medium text-slate-700'
                          }`}
                          title={getFolderLabel(folder)}
                        >
                          <span className="truncate">{getFolderLabel(folder)}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="relative min-w-0 lg:w-[360px] lg:shrink-0">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Cerca per nome o cartella"
                  className="w-full rounded-lg border border-slate-200 py-2 pl-3 pr-11 text-sm outline-none transition-colors focus:border-[#1F3A8B]"
                />
                <Search className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              </div>
            </div>

            {error && (
              <div className="mb-4 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {loading ? (
              <div className="rounded-lg border border-dashed border-slate-200 px-5 py-10 text-center text-sm text-slate-500">
                Caricamento documenti...
              </div>
            ) : visibleDocuments.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 px-5 py-10 text-center">
                <FolderOpen className="mx-auto mb-3 h-8 w-8 text-slate-300" />
                <p className="text-sm font-semibold text-slate-700">Nessun documento trovato</p>
                <p className="mt-1 text-xs text-slate-500">Modifica la ricerca o aggiorna la lista.</p>
              </div>
            ) : (
              <div className="overflow-hidden rounded-lg border border-slate-200">
                <div className="max-h-[560px] overflow-y-auto overflow-x-hidden">
                  <table className="w-full table-fixed divide-y divide-slate-200 text-left text-sm">
                    <thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500">
                      <tr>
                        <th className="w-[55%] px-4 py-3 text-left font-bold">Nome</th>
                        <th className="w-[10%] px-3 py-3 text-center font-bold">Cartella</th>
                        <th className="w-[8%] px-3 py-3 text-center font-bold">Dimensione</th>
                        <th className="w-[17%] px-3 py-3 text-center font-bold">Ultima modifica</th>
                        <th className="w-[8%] px-3 py-3 text-center font-bold">Azioni</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {visibleDocuments.map((document) => (
                        <tr key={document.key} className="hover:bg-slate-50">
                          <td className="px-4 py-3">
                            <div className="flex items-start gap-3">
                              <FileTypeBadge name={document.name} compact />
                              <div className="min-w-0">
                                <p className="truncate font-semibold text-slate-800" title={document.name}>
                                  {document.name}
                                </p>
                                <p className="mt-1 truncate text-xs text-slate-400" title={document.key}>
                                  {document.key}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-3 py-3 text-center text-xs text-slate-500">
                            <p className="truncate" title={document.folder}>
                              {getFolderLabel(document.folder)}
                            </p>
                          </td>
                          <td className="px-3 py-3 text-center text-slate-600">
                            <p className="truncate">{formatFileSize(document.size)}</p>
                          </td>
                          <td className="px-3 py-3 text-center text-slate-600">
                            <p className="truncate" title={formatDate(document.lastModified)}>
                              {formatDate(document.lastModified)}
                            </p>
                          </td>
                          <td className="px-3 py-3">
                            <div className="relative flex justify-center">
                              <button
                                onClick={() =>
                                  setOpenActionKey((current) =>
                                    current === document.key ? null : document.key
                                  )
                                }
                                disabled={actionLoading === document.key}
                                className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
                                title="Azioni"
                              >
                                <MoreVertical className="h-4 w-4" />
                              </button>

                              {openActionKey === document.key && (
                                <div className="absolute right-4 top-10 z-30 w-40 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 text-left shadow-lg">
                                  <button
                                    onClick={() => handleDownload(document)}
                                    className="flex w-full items-center gap-2 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                                  >
                                    <Download className="h-4 w-4" />
                                    Scarica
                                  </button>

                                  <button
                                    onClick={() => openDeleteModal(document)}
                                    disabled={actionLoading === document.key}
                                    className="flex w-full items-center gap-2 px-3 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                    Elimina
                                  </button>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#1F3A8B]/10 text-[#1F3A8B]">
                  <FileUp className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Upload documento</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Seleziona la cartella e uno o piu file da salvare in documents/.
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setSelectedFiles([]);
                  setUseCustomFolder(false);
                  setCustomFolderName('');
                }}
                disabled={actionLoading === 'upload'}
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 disabled:opacity-60"
                title="Chiudi"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-5">
              <label className="block text-xs font-bold uppercase text-slate-500">
                Cartella
                <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto]">
                  <select
                    value={selectedFolder}
                    onChange={(event) => setSelectedFolder(event.target.value)}
                    disabled={useCustomFolder}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium normal-case text-slate-700 outline-none transition-colors focus:border-[#1F3A8B] disabled:bg-slate-100 disabled:text-slate-400"
                  >
                    {availableFolders.map((folder) => (
                      <option key={folder} value={folder}>
                        {getFolderLabel(folder)}
                      </option>
                    ))}
                  </select>
                  <label className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold normal-case text-slate-600">
                    <input
                      type="checkbox"
                      checked={useCustomFolder}
                      onChange={(event) => setUseCustomFolder(event.target.checked)}
                      className="h-4 w-4 accent-[#1F3A8B]"
                    />
                    Nuova
                  </label>
                </div>
              </label>

              {useCustomFolder && (
                <label className="block text-xs font-bold uppercase text-slate-500">
                  Nome nuova cartella
                  <input
                    value={customFolderName}
                    onChange={(event) => setCustomFolderName(event.target.value)}
                    placeholder="es. nuova-fonte"
                    className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium normal-case text-slate-700 outline-none transition-colors focus:border-[#1F3A8B]"
                  />
                  <span className="mt-1 block text-[11px] font-medium normal-case text-slate-400">
                    Verra creata sotto documents/regulatory/.
                  </span>
                </label>
              )}

              <label className="block text-xs font-bold uppercase text-slate-500">
                File
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="mt-2 flex flex-col gap-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-3 sm:flex-row sm:items-center">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex w-full items-center justify-center rounded-lg bg-[#1F3A8B] px-4 py-2 text-sm font-semibold normal-case text-white transition-colors hover:bg-[#172554] sm:w-auto"
                  >
                    Scegli file
                  </button>
                  <span className="min-w-0 text-sm font-medium normal-case text-slate-500">
                    {selectedFiles.length === 0
                      ? 'Nessun file selezionato'
                      : selectedFiles.length === 1
                        ? selectedFiles[0].name
                        : `${selectedFiles.length} file selezionati`}
                  </span>
                </div>
              </label>

              {selectedFiles.length > 0 && (
                <div className="max-h-52 space-y-2 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
                  {selectedFiles.map((file, index) => (
                    <div
                      key={`${file.name}-${file.size}`}
                      className="flex items-center gap-3 rounded-lg bg-white px-3 py-2 text-sm text-slate-700"
                    >
                      <FileTypeBadge name={file.name} compact />
                      <span className="min-w-0 flex-1 truncate font-medium">{file.name}</span>
                      <span className="shrink-0 text-xs text-slate-400">{formatFileSize(file.size)}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveSelectedFile(index)}
                        className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
                        title="Rimuovi file"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setSelectedFiles([]);
                  setUseCustomFolder(false);
                  setCustomFolderName('');
                }}
                disabled={actionLoading === 'upload'}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-60"
              >
                Annulla
              </button>
              <button
                onClick={handleUpload}
                disabled={selectedFiles.length === 0 || actionLoading === 'upload'}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1F3A8B] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#172554] disabled:bg-slate-300"
              >
                <Upload className="h-4 w-4" />
                {actionLoading === 'upload'
                  ? 'Caricamento...'
                  : selectedFiles.length > 1
                    ? `Carica ${selectedFiles.length} file`
                    : 'Carica documento'}
              </button>
            </div>
          </div>
        </div>
      )}

      {documentToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-600">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-slate-900">Eliminare definitivamente?</h2>
                {deleteConfirmationStep === 1 && (
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Questa azione eliminera il documento da S3. L'operazione e irreversibile.
                  </p>
                )}
                {deleteConfirmationStep === 2 && (
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Conferma ancora: il documento verra rimosso definitivamente e non potra essere recuperato dalla schermata.
                  </p>
                )}
                {deleteConfirmationStep === 3 && (
                  <div className="mt-2">
                    <p className="text-sm leading-6 text-slate-500">
                      Per completare, scrivi <span className="font-bold text-red-600">ELIMINA</span>.
                    </p>
                    <input
                      value={deleteConfirmationText}
                      onChange={(event) => setDeleteConfirmationText(event.target.value)}
                      placeholder="ELIMINA"
                      className="mt-3 w-full rounded-lg border border-red-100 px-3 py-2 text-sm font-semibold text-slate-700 outline-none transition-colors focus:border-red-500"
                    />
                  </div>
                )}
                <p className="mt-3 truncate rounded-lg bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                  {documentToDelete.name}
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={closeDeleteModal}
                disabled={actionLoading === documentToDelete.key}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-60"
              >
                Annulla
              </button>
              {deleteConfirmationStep < 3 ? (
                <button
                  onClick={() => setDeleteConfirmationStep((step) => step + 1)}
                  disabled={actionLoading === documentToDelete.key}
                  className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:bg-slate-300"
                >
                  Conferma
                </button>
              ) : (
                <button
                  onClick={handlePermanentDelete}
                  disabled={
                    actionLoading === documentToDelete.key
                    || deleteConfirmationText.trim() !== 'ELIMINA'
                  }
                  className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:bg-slate-300"
                >
                  {actionLoading === documentToDelete.key ? 'Eliminazione...' : 'Elimina definitivamente'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CheckComplianceDocuments;
