import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Trees, Plus, LogIn, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTheme } from "@/hooks/useTheme";
import { api, ApiError, setCookie } from "@/lib/api";
import type { Room } from "@/types";

export default function HomePage() {
  const [mode, setMode] = useState<"choose" | "create" | "join">("choose");
  const [roomName, setRoomName] = useState("");
  const [passcode, setPasscode] = useState("");
  const [nickname, setNickname] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const resolveNickname = () => nickname.trim() || "Anonymous";

  const handleCreate = async () => {
    if (!passcode.trim()) {
      setError("请输入口令");
      return;
    }
    const nick = resolveNickname();
    setCookie("df_nickname", nick);
    setLoading(true);
    setError("");
    try {
      const room = await api.post<Room>("/api/rooms", {
        name: roomName.trim() || "匿名聊天室",
        passcode: passcode.trim(),
        nickname: nick,
      });
      navigate(`/room/${room.id}`);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail);
      } else {
        setError("创建失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async () => {
    if (!passcode.trim()) {
      setError("请输入口令");
      return;
    }
    const nick = resolveNickname();
    setCookie("df_nickname", nick);
    setLoading(true);
    setError("");
    try {
      const room = await api.post<Room>("/api/rooms/join", {
        passcode: passcode.trim(),
        nickname: nick,
      });
      navigate(`/room/${room.id}`);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail);
      } else {
        setError("加入失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-gradient-to-br from-background via-background to-primary/5">
      {/* Theme toggle */}
      <div className="fixed top-4 right-4 z-50">
        <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="切换主题">
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>

      {/* Logo & Title */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <Trees className="h-10 w-10 text-primary" />
          <h1 className="text-4xl font-bold tracking-tight">DarkForest</h1>
        </div>
        <p className="text-muted-foreground text-lg">匿名聊天，口令即入，阅后即焚</p>
      </div>

      {/* Main Card */}
      <Card className="w-full max-w-md">
        {mode === "choose" && (
          <>
            <CardHeader className="text-center">
              <CardTitle>选择你的操作</CardTitle>
              <CardDescription>创建一个新的聊天空间，或加入已有的空间</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Button
                size="lg"
                className="w-full h-14 text-base"
                onClick={() => setMode("create")}
              >
                <Plus className="mr-2 h-5 w-5" />
                创建聊天空间
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="w-full h-14 text-base"
                onClick={() => setMode("join")}
              >
                <LogIn className="mr-2 h-5 w-5" />
                加入聊天空间
              </Button>
            </CardContent>
          </>
        )}

        {mode === "create" && (
          <>
            <CardHeader>
              <CardTitle>创建聊天空间</CardTitle>
              <CardDescription>设置口令，其他人可以用口令加入</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="room-name">空间名称（可选）</Label>
                <Input
                  id="room-name"
                  placeholder="给空间起个名字..."
                  value={roomName}
                  onChange={(e) => setRoomName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="passcode">口令 *</Label>
                <Input
                  id="passcode"
                  placeholder="输入口令"
                  value={passcode}
                  onChange={(e) => setPasscode(e.target.value)}
                  maxLength={20}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nickname">昵称</Label>
                <Input
                  id="nickname"
                  placeholder="Anonymous"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  maxLength={50}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={() => { setMode("choose"); setError(""); }}>
                  返回
                </Button>
                <Button className="flex-1" onClick={handleCreate} disabled={loading}>
                  {loading ? "创建中..." : "创建"}
                </Button>
              </div>
            </CardContent>
          </>
        )}

        {mode === "join" && (
          <>
            <CardHeader>
              <CardTitle>加入聊天空间</CardTitle>
              <CardDescription>输入口令加入已有的聊天空间</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="join-passcode">口令 *</Label>
                <Input
                  id="join-passcode"
                  placeholder="输入口令"
                  value={passcode}
                  onChange={(e) => setPasscode(e.target.value)}
                  maxLength={20}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="join-nickname">昵称</Label>
                <Input
                  id="join-nickname"
                  placeholder="Anonymous"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  maxLength={50}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={() => { setMode("choose"); setError(""); }}>
                  返回
                </Button>
                <Button className="flex-1" onClick={handleJoin} disabled={loading}>
                  {loading ? "加入中..." : "加入"}
                </Button>
              </div>
            </CardContent>
          </>
        )}
      </Card>

      <p className="mt-6 text-xs text-muted-foreground">
        无活动超过配置时间后空间将自动销毁 · 消息不会永久存储
      </p>
    </div>
  );
}
