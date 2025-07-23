export interface Message {
  sender: 'user' | 'ai';
  content: string;
  citations?: string[];
}

export interface ApiMessage {
  id: number;
  conversation: string;
  content: string;
  file: string | null;
  created_at: string;
  is_user: boolean;
  citations?: string[]; 
}

export interface Chat {
  id: number | string;
  name: string;
}

export interface ApiChatResponse {
  id: string;
  name: string;
  user: number;
  created_at: string;
  messages: ApiMessage[];
}