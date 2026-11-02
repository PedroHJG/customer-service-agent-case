"use client";

import { useEffect, useRef } from "react";
import { isToolUIPart } from "ai";
import { Header } from "@/components/layout/Header";
import { useAgentChat } from "@/hooks/useAgentChat";
import { useChatStore } from "@/store/useChatStore";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

export function ChatArea({ chatId }: { chatId: string }) {
  const { messages, send, status, isBusy, error } = useAgentChat(chatId);
  const ensureSession = useChatStore((s) => s.ensureSession);
  const title = useChatStore((s) => s.sessions.find((x) => x.id === chatId)?.title ?? "Cliente");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => ensureSession(chatId), [chatId, ensureSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const lastMessage = messages.at(-1);
  const isConsulting =
    isBusy && lastMessage?.role === "assistant" && lastMessage.parts.some((p) => isToolUIPart(p) && !p.state.startsWith("output"));

  const headerStatus = isConsulting ? "consultando dados..." : isBusy ? "digitando..." : "online";

  return (
    <div className="flex h-full flex-col">
      <Header title={title} status={headerStatus} />

      <div className="flex-1 overflow-y-auto bg-wa-chat-bg px-[8%] py-4">
        <div className="flex flex-col gap-3">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {status === "submitted" && <TypingIndicator />}
          {error && (
            <p className="text-center text-xs text-destructive">
              Não foi possível falar com o atendente agora. Tente novamente.
            </p>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <ChatInput onSend={send} disabled={isBusy} />
    </div>
  );
}
