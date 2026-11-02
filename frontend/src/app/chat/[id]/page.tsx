import { ChatArea } from "@/components/chat/ChatArea";

export default async function ChatPage({ params }: PageProps<"/chat/[id]">) {
  const { id } = await params;

  // key força um novo estado do useChat ao trocar de conversa (contexto isolado)
  return <ChatArea key={id} chatId={id} />;
}
