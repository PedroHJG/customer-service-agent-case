"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { AGENT_NAME } from "@/lib/constants";
import { cn, formatChatTime } from "@/lib/utils";
import { chatApi } from "@/services/api";
import { useChatStore } from "@/store/useChatStore";

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { sessions, createSession, removeSession } = useChatStore();

  // Lê o localStorage só depois de montar (ver skipHydration no store)
  useEffect(() => {
    useChatStore.persist.rehydrate();
  }, []);

  const handleNewChat = () => router.push(`/chat/${createSession()}`);

  const handleDelete = (id: string) => {
    removeSession(id);
    chatApi.deleteChat(id).catch(() => {});
    if (pathname === `/chat/${id}`) router.push("/");
  };

  return (
    <aside className="flex w-80 shrink-0 flex-col border-r bg-background">
      <div className="flex h-16 items-center justify-between bg-wa-header px-4">
        <span className="font-semibold">{AGENT_NAME}</span>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleNewChat}
          aria-label="Nova conversa"
        >
          <MessageSquarePlus className="size-5" />
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto">
        {sessions.length === 0 && (
          <p className="p-6 text-center text-sm text-muted-foreground">
            Nenhuma conversa ainda. Clique em + para simular um novo cliente.
          </p>
        )}

        {sessions.map((session) => {
          const isActive = pathname === `/chat/${session.id}`;
          return (
            <div
              key={session.id}
              className={cn(
                "group flex items-center border-b hover:bg-muted",
                isActive && "bg-muted",
              )}
            >
              <Link
                href={`/chat/${session.id}`}
                className="flex min-w-0 flex-1 items-center gap-3 px-4 py-3"
              >
                <Avatar>
                  <AvatarFallback>{session.title.slice(-2)}</AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate font-medium">
                      {session.title}
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatChatTime(session.updatedAt)}
                    </span>
                  </div>
                  <p className="truncate text-sm text-muted-foreground">
                    {session.lastMessage ?? "Nova conversa"}
                  </p>
                </div>
              </Link>
              <Button
                variant="ghost"
                size="icon-sm"
                className="mr-2 opacity-0 group-hover:opacity-100"
                onClick={() => handleDelete(session.id)}
                aria-label="Apagar conversa"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
