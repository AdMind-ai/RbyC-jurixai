export interface Message {
  sender: 'user' | 'ai';
  content: string;
}

export interface ApiMessage {
  id: number
  conversation: string
  content: string
  created_at: string
  is_user: boolean
  // Optional citations saved on the message (from backend ChatMessage.citations)
  citations?: Array<{
    id?: string
    title?: string
    url?: string
    type?: string
  }>
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