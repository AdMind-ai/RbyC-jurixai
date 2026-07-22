
import React from 'react';
import { Search, FileText, Shield, Bot, Briefcase, Newspaper } from 'lucide-react';
import { ToolId, SubToolId } from '../types/types';

export const TOOL_CONFIG: Record<string, { name: string; icon: React.ReactNode; color: string; description: string }> = {
  [ToolId.RICERCA_DOCUMENTALE]: {
    name: 'Ricerca documentale',
    icon: <Search className="w-5 h-5" />,
    color: '#1F3A8B',
    description: 'Analisi semantica e ricerca avanzata nell\'archivio documenti.'
  },
  [ToolId.DRAFT_DOCUMENT]: {
    name: 'Draft Document',
    icon: <FileText className="w-5 h-5" />,
    color: '#1F3A8B',
    description: 'Generazione bozze legali e atti partendo da prompt strutturati.'
  },
  [ToolId.CHECK_COMPLIANCE]: {
    name: 'Check compliance',
    icon: <Shield className="w-5 h-5" />,
    color: '#1F3A8B',
    description: 'Verifica automatizzata della conformità normativa e GDPR.'
  },
  [ToolId.CHAT_ASSISTANT]: {
    name: 'Chat Assistant',
    icon: <Bot className="w-5 h-5" />,
    color: '#1F3A8B',
    description: 'Interfaccia conversazionale per brainstorming e supporto rapido.'
  },
  [ToolId.NEWSLETTER_PILL]: {
    name: 'Newsletter & PILL',
    icon: <Newspaper className="w-5 h-5" />,
    color: '#1F3A8B',
    description: 'Generazione di newsletter normative e contenuti formativi.'
  },
  [ToolId.SEGRETERIA_SOCIETARIA]: {
    name: 'Segreteria Societaria (Totale)',
    icon: <Briefcase className="w-5 h-5" />,
    color: '#1F3A8B',
    description: 'Gestione adempimenti societari con strumenti AI dedicati.'
  },
  [SubToolId.DOCUMENTI_AI]: {
    name: 'Documenti AI',
    icon: <FileText className="w-5 h-5" />,
    color: '#1F3A8B',
    description: ''
  },
  [SubToolId.ASSISTENTE_LEGALE]: {
    name: 'Assistente Legale',
    icon: <Bot className="w-5 h-5" />,
    color: '#1F3A8B',
    description: ''
  }
};

export const METRIC_LABELS: Record<string, string> = {
  [ToolId.RICERCA_DOCUMENTALE]: 'Interazioni registrate',
  [ToolId.CHECK_COMPLIANCE]: 'Interazioni registrate',
  [ToolId.DRAFT_DOCUMENT]: 'Interazioni registrate',
  [ToolId.CHAT_ASSISTANT]: 'Interazioni registrate',
  [ToolId.NEWSLETTER_PILL]: 'Interazioni registrate',
  [ToolId.SEGRETERIA_SOCIETARIA]: 'Interazioni registrate',
  [SubToolId.DOCUMENTI_AI]: 'Interazioni registrate',
  [SubToolId.ASSISTENTE_LEGALE]: 'Interazioni registrate'
};

export const formatEuro = (val: number) =>
  val.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
