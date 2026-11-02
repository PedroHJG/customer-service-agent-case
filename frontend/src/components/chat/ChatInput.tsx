"use client";

import { useState, type FormEvent } from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (disabled || !text.trim()) return;
    onSend(text);
    setText("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 bg-wa-header px-4 py-3">
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Digite uma mensagem"
        className="h-10 bg-background"
        autoFocus
      />
      <Button type="submit" size="icon-lg" disabled={disabled || !text.trim()} aria-label="Enviar">
        <SendHorizontal className="size-5" />
      </Button>
    </form>
  );
}
