import { ShieldAlert } from "lucide-react";

/** Aviso visual quando o backend sinaliza que a pergunta fugiu do escopo da loja. */
export function GuardrailAlert({ reason }: { reason: string }) {
  return (
    <div className="flex justify-center">
      <span className="flex items-center gap-1.5 rounded-md bg-amber-100 px-3 py-1 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
        <ShieldAlert className="size-3.5" />
        Fora do escopo: {reason}
      </span>
    </div>
  );
}
