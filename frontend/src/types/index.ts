import type { UIMessage } from "ai";

/**
 * Ferramentas que o agente (backend) pode chamar.
 * O nome precisa bater com o `toolName` emitido pelo backend no stream,
 * pois o AI SDK cria partes do tipo `tool-<toolName>` na mensagem.
 */
export type AgentToolName =
  | "buscar_produtos"
  | "consultar_pedido"
  | "consultar_politicas"
  | "listar_promocoes";

/** Payload da parte customizada `data-guardrail`, enviada quando a pergunta foge do escopo. */
export interface GuardrailData {
  reason: string;
}

/** Partes de dados customizadas (`data-*`) que o backend pode enviar. */
export type AgentDataParts = {
  guardrail: GuardrailData;
};

/** Mensagem tipada usada em todo o frontend. */
export type AgentMessage = UIMessage<unknown, AgentDataParts>;

/** Uma conversa listada na sidebar (cada uma é um cliente com contexto isolado). */
export interface ChatSession {
  id: string;
  title: string;
  lastMessage?: string;
  updatedAt: number;
}

export interface APIError {
  status: number;
  detail: string;
}
