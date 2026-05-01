import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import {
  Send,
  ArrowLeft,
  Users,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api, ApiError } from "@/lib/api";
import type { Room, WSMessage } from "@/types";

interface ChatMessage {
  id: string;
  type: "message" | "system" | "join" | "leave" | "error";
  content: string;
  nickname?: string;
  timestamp?: string;
}

export default function ChatPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const [searchParams] = useSearchParams();
  const nickname = searchParams.get("nickname") || "Anonymous";
  const navigate = useNavigate();

  const [room, setRoom] = useState<Room | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [onlineCount, setOnlineCount] = useState(0);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const wsUrl =
    roomId && room
      ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/${roomId}?nickname=${encodeURIComponent(nickname)}`
      : null;

  const handleMessage = useCallback((msg: WSMessage) => {
    const chatMsg: ChatMessage = {
      id: crypto.randomUUID(),
      type: msg.type as ChatMessage["type"],
      content: msg.content,
      nickname: msg.nickname || undefined,
      timestamp: msg.timestamp || new Date().toISOString(),
    };
    setMessages((prev) => [...prev, chatMsg]);

    if (msg.online_count !== null && msg.online_count !== undefined) {
      setOnlineCount(msg.online_count);
    }

    // If room is being destroyed, show alert
    if (msg.type === "system" && msg.content.includes("destroyed")) {
      setTimeout(() => navigate("/"), 3000);
    }
  }, [navigate]);

  const { isConnected, send, disconnect } = useWebSocket(wsUrl, {
    onMessage: handleMessage,
    onError: () => setError("连接中断，尝试重连中..."),
  });

  // Fetch room info
  useEffect(() => {
    if (!roomId) return;
    api
      .get<Room>(`/api/rooms/${roomId}`)
      .then(setRoom)
      .catch((e) => {
        if (e instanceof ApiError) setError(e.detail);
        else setError("无法加载房间信息");
      });
  }, [roomId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const content = input.trim();
    if (!content || !isConnected) return;
    send({ type: "message", content });
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleLeave = () => {
    disconnect();
    navigate("/");
  };

  if (error && !room) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-destructive mx-auto" />
          <p className="text-lg text-muted-foreground">{error}</p>
          <Button onClick={() => navigate("/")}>返回主页</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={handleLeave}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h2 className="font-semibold text-sm sm:text-base truncate max-w-[200px] sm:max-w-[400px]">
              {room?.name || "加载中..."}
            </h2>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Users className="h-3 w-3" />
              <span>{onlineCount} 在线</span>
              <Clock className="h-3 w-3 ml-1" />
              <span>{room?.timeout_minutes}分钟无活动销毁</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={isConnected ? "default" : "secondary"}>
            {isConnected ? "已连接" : "连接中..."}
          </Badge>
        </div>
      </header>

      {/* Messages */}
      <ScrollArea className="flex-1 px-4 py-3">
        <div className="space-y-3 max-w-3xl mx-auto">
          {messages.map((msg) => (
            <div key={msg.id}>
              {msg.type === "message" ? (
                <div className="flex flex-col">
                  <span className="text-xs text-primary font-medium mb-0.5">
                    {msg.nickname}
                  </span>
                  <div className="bg-muted rounded-lg px-3 py-2 max-w-[80%] sm:max-w-[70%] break-words text-sm">
                    {msg.content}
                  </div>
                  {msg.timestamp && (
                    <span className="text-[10px] text-muted-foreground mt-0.5">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              ) : (
                <div className="text-center">
                  <span
                    className={`text-xs px-3 py-1 rounded-full ${
                      msg.type === "error"
                        ? "bg-destructive/10 text-destructive"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {msg.content}
                  </span>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      <Separator />

      {/* Input */}
      <div className="p-3 sm:p-4 shrink-0">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息..."
            disabled={!isConnected}
            className="flex-1"
            maxLength={2000}
          />
          <Button onClick={handleSend} disabled={!isConnected || !input.trim()} size="icon">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
