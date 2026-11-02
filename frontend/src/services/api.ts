import { API_URL } from "@/lib/constants";
import type { AgentMessage, APIError } from "@/types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error: APIError = { status: response.status, detail: body.detail ?? response.statusText };
    throw error;
  }

  return response.status === 204 ? (undefined as T) : response.json();
}

/** Histórico de uma conversa (rotas não-streaming). O streaming fica no useAgentChat. */
export const chatApi = {
  getMessages: (chatId: string) => request<AgentMessage[]>(`/chats/${chatId}/messages`),
  deleteChat: (chatId: string) => request<void>(`/chats/${chatId}`, { method: "DELETE" }),
};
