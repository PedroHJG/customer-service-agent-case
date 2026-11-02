import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { TOOL_LABELS } from "@/lib/constants";
import type { AgentToolName } from "@/types";

interface ToolCallBadgeProps {
  toolName: string;
  state: "input-streaming" | "input-available" | "output-available" | "output-error" | string;
}

/** Mostra ao usuário que o agente está consultando dados/políticas em tempo real. */
export function ToolCallBadge({ toolName, state }: ToolCallBadgeProps) {
  const labels = TOOL_LABELS[toolName as AgentToolName] ?? { running: "Consultando...", done: "Consulta concluída" };

  const content = {
    "output-available": { icon: <CheckCircle2 className="size-3.5 text-wa-accent" />, text: labels.done },
    "output-error": { icon: <XCircle className="size-3.5 text-destructive" />, text: "Falha na consulta" },
  }[state] ?? { icon: <Loader2 className="size-3.5 animate-spin" />, text: labels.running };

  return (
    <div className="flex justify-center">
      <span className="flex items-center gap-1.5 rounded-full bg-wa-header px-3 py-1 text-xs text-muted-foreground shadow-sm">
        {content.icon}
        {content.text}
      </span>
    </div>
  );
}
