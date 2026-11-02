"use client";

import { useEffect, useMemo } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { API_URL } from "@/lib/constants";
import { getMessageText, truncate } from "@/lib/utils";
import { chatApi } from "@/services/api";
import { useChatStore } from "@/store/useChatStore";
import type { AgentMessage } from "@/types";

/**
 * Wrapper do useChat (Vercel AI SDK) conectado ao backend FastAPI.
 * Cada chatId é uma conversa isolada: o backend usa o mesmo id como thread do agente.
 */
export function useAgentChat(chatId: string) {
  const updateSession = useChatStore((s) => s.updateSession);

  const transport = useMemo(
    () =>
      new DefaultChatTransport<AgentMessage>({
        api: `${API_URL}/chat`,
        // O backend guarda o histórico, então enviamos só a última mensagem
        prepareSendMessagesRequest: ({ id, messages }) => ({
          body: { chat_id: id, message: messages.at(-1) },
        }),
      }),
    [],
  );

  const chat = useChat<AgentMessage>({
    id: chatId,
    transport,
    onFinish: ({ message }) => {
      updateSession(chatId, { lastMessage: truncate(getMessageText(message)), updatedAt: Date.now() });
    },
  });

  const { setMessages } = chat;

  // Recupera o histórico salvo no backend ao abrir a conversa
  useEffect(() => {
    chatApi
      .getMessages(chatId)
      .then(setMessages)
      .catch(() => {
        // Conversa nova ou backend fora do ar: começa vazia
      });
  }, [chatId, setMessages]);

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    updateSession(chatId, { lastMessage: truncate(trimmed), updatedAt: Date.now() });
    chat.sendMessage({ text: trimmed });
  };

  return {
    ...chat,
    send,
    isBusy: chat.status === "submitted" || chat.status === "streaming",
  };
}
