import type { AgentToolName } from "@/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const AGENT_NAME = "Empório da Música";

/** Texto exibido na UI enquanto cada ferramenta está rodando / depois que terminou. */
export const TOOL_LABELS: Record<AgentToolName, { running: string; done: string }> = {
  buscar_produtos: { running: "Consultando catálogo e estoque...", done: "Catálogo consultado" },
  consultar_pedido: { running: "Consultando status do pedido...", done: "Pedido consultado" },
  consultar_politicas: { running: "Consultando políticas da loja...", done: "Políticas consultadas" },
  listar_promocoes: { running: "Buscando promoções ativas...", done: "Promoções consultadas" },
};
