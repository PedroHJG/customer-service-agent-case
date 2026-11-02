import { isToolUIPart, getToolName } from "ai";
import { cn } from "@/lib/utils";
import type { AgentMessage } from "@/types";
import { GuardrailAlert } from "./GuardrailAlert";
import { ToolCallBadge } from "./ToolCallBadge";

/**
 * Renderiza uma mensagem parte a parte: textos viram balões,
 * chamadas de ferramenta viram badges de status e `data-guardrail` vira alerta.
 */
export function MessageBubble({ message }: { message: AgentMessage }) {
  const isUser = message.role === "user";

  return (
    <div className="flex flex-col gap-2">
      {message.parts.map((part, index) => {
        const key = `${message.id}-${index}`;

        if (part.type === "text") {
          return (
            <div key={key} className={cn("flex", isUser ? "justify-end" : "justify-start")}>
              <div
                className={cn(
                  "max-w-[75%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm shadow-sm",
                  isUser ? "rounded-tr-none bg-wa-bubble-out" : "rounded-tl-none bg-wa-bubble-in",
                )}
              >
                {part.text}
              </div>
            </div>
          );
        }

        if (isToolUIPart(part)) {
          return <ToolCallBadge key={key} toolName={getToolName(part)} state={part.state} />;
        }

        if (part.type === "data-guardrail") {
          return <GuardrailAlert key={key} reason={part.data.reason} />;
        }

        return null;
      })}
    </div>
  );
}
