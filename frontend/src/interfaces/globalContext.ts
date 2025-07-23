import { CompanyInfoAdm } from './companyInfoInterface';

export interface GlobalContextType {
  companyInfoAdm: CompanyInfoAdm | null;
  awaitingDeepResponse: AwaitingDeepResponseType | null;
  setAwaitingDeepResponse: React.Dispatch<React.SetStateAction<AwaitingDeepResponseType | null>>;
  selectedLawTab: string | null;
  setSelectedLawTab: React.Dispatch<React.SetStateAction<string | null>>;
}

export interface ApiMessage {
  id: number|string;
  conversation: string;
  content: string;
  file: string | null;
  created_at: string;
  is_user: boolean;
  citations?: string[];
}

export interface AwaitingDeepResponseType {
  conversationId: string | number;
  messageId: string | number;
  placeholderText: string;
  chatName: string;
}