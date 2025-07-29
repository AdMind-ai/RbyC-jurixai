export interface Message {
  sender: 'user' | 'ai';
  content: string;
}

export interface ApiMessage {
  id: number;
  conversation: string;
  content: string;
  created_at: string;
  is_user: boolean;
}

export interface Chat {
  id: number | string;
  name: string;
  thread_id?: string | null;
}

export interface ApiChatResponse {
  id: string;
  name: string;
  user: number;
  created_at: string;
  messages: ApiMessage[];
  threads: { thread_id: string; created_at: string; active: boolean }[]; 
  thread_id?: string | null;
}