import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatSession } from "@/types";

interface ChatStore {
  sessions: ChatSession[];
  createSession: () => string;
  ensureSession: (id: string) => void;
  updateSession: (id: string, patch: Partial<Omit<ChatSession, "id">>) => void;
  removeSession: (id: string) => void;
}

/**
 * Guarda apenas os metadados das conversas (sidebar).
 * As mensagens em si ficam no backend (fonte da verdade do contexto do agente).
 */
export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],

      createSession: () => {
        const id = crypto.randomUUID();
        const number = get().sessions.length + 1;
        set((state) => ({
          sessions: [{ id, title: `Cliente ${number}`, updatedAt: Date.now() }, ...state.sessions],
        }));
        return id;
      },

      // Garante que uma conversa aberta via URL apareça na sidebar
      ensureSession: (id) => {
        if (get().sessions.some((s) => s.id === id)) return;
        set((state) => ({
          sessions: [{ id, title: `Cliente ${state.sessions.length + 1}`, updatedAt: Date.now() }, ...state.sessions],
        }));
      },

      updateSession: (id, patch) =>
        set((state) => ({
          sessions: state.sessions
            .map((s) => (s.id === id ? { ...s, ...patch } : s))
            .sort((a, b) => b.updatedAt - a.updatedAt),
        })),

      removeSession: (id) => set((state) => ({ sessions: state.sessions.filter((s) => s.id !== id) })),
    }),
    {
      name: "emporio-chat-sessions",
      // Evita hydration mismatch: o localStorage só é lido no client (ver Sidebar)
      skipHydration: true,
    },
  ),
);
