import { Store } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { AGENT_NAME } from "@/lib/constants";

interface HeaderProps {
  title: string;
  status: string;
}

export function Header({ title, status }: HeaderProps) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b bg-wa-header px-4">
      <Avatar>
        <AvatarFallback className="bg-wa-accent text-white">
          <Store className="size-5" />
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="truncate font-medium">
          {AGENT_NAME} <span className="text-muted-foreground">· {title}</span>
        </p>
        <p className="text-xs text-muted-foreground">{status}</p>
      </div>
    </header>
  );
}
