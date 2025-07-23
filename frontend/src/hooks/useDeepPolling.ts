import { useEffect, useRef } from "react";
import { fetchWithAuth } from "../api/fetchWithAuth";
import { toast } from "react-toastify";
import { ApiMessage, AwaitingDeepResponseType } from "../interfaces/globalContext";

export function useDeepPolling(awaitingDeepResponse: AwaitingDeepResponseType | null, setAwaitingDeepResponse: React.Dispatch<React.SetStateAction<AwaitingDeepResponseType | null>>) {
  const pollingInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!awaitingDeepResponse) return;
    pollingInterval.current = setInterval(async () => {
      try {
        const resp = await fetchWithAuth(`/openai/chat/${awaitingDeepResponse.conversationId}/`);
        if (!resp.ok) return;
        const data = await resp.json();
        const messages: ApiMessage[] = data.messages || [];
        const msg = messages.find((m) => String(m.id) === String(awaitingDeepResponse.messageId));
        if (msg && msg.content && msg.content !== awaitingDeepResponse.placeholderText) {
          toast.success("La tua deep research è pronta! Chat: " + awaitingDeepResponse.chatName);
          window.dispatchEvent(
            new CustomEvent("deepResearchReady", {
              detail: {
                conversationId: awaitingDeepResponse.conversationId,
                messageId: awaitingDeepResponse.messageId,
                chatName: awaitingDeepResponse.chatName,
                content: msg.content,
                citations: msg.citations || [],
              },
            })
          );
          setAwaitingDeepResponse(null);
          if (pollingInterval.current) clearInterval(pollingInterval.current);
        }
      } catch {console.error("Error fetching deep research response");}
    }, 3000);
    return () => {
      if (pollingInterval.current) clearInterval(pollingInterval.current);
    };
  }, [awaitingDeepResponse, setAwaitingDeepResponse]);
}