import { Music } from "lucide-react";

/** Tela vazia (estilo WhatsApp Web) mostrada quando nenhuma conversa está aberta. */
export default function Home() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 border-b-4 border-wa-accent bg-wa-header text-center">
      <Music className="size-16 text-wa-accent" />
      <h1 className="text-2xl font-light">Empório da Música · Atendimento</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        Selecione uma conversa ou inicie uma nova para simular um cliente. Cada conversa tem seu próprio contexto
        isolado no agente.
      </p>
    </div>
  );
}
