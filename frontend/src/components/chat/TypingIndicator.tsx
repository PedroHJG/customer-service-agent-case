/** Balão "digitando..." exibido enquanto o agente processa e ainda não começou a responder. */
export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-1 rounded-lg rounded-tl-none bg-wa-bubble-in px-4 py-3 shadow-sm">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="size-2 animate-bounce rounded-full bg-muted-foreground"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>
    </div>
  );
}
