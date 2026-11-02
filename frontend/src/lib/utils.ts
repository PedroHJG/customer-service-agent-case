import type { AgentMessage } from "@/types";

export { cn } from "cn";

const timeFormatter = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });
const dateFormatter = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" });

/** Formata como o WhatsApp: hora se for hoje, data caso contrário. */
export function formatChatTime(timestamp: number): string {
  const date = new Date(timestamp);
  const isToday = date.toDateString() === new Date().toDateString();
  return isToday ? timeFormatter.format(date) : dateFormatter.format(date);
}

/** Junta todas as partes de texto de uma mensagem. */
export function getMessageText(message: AgentMessage): string {
  return message.parts
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("");
}

export function truncate(text: string, max = 40): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
