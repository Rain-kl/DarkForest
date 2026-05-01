import { useState, useEffect } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import {
  LayoutDashboard,
  DoorOpen,
  Settings,
  Users,
  Trash2,
  RefreshCw,
  ArrowLeft,
  Moon,
  Sun,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/hooks/useTheme";
import { api, ApiError } from "@/lib/api";
import type { RoomSummary, SystemStats, ConfigResponse } from "@/types";

type Tab = "dashboard" | "rooms" | "config";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [rooms, setRooms] = useState<RoomSummary[]>([]);
  const [configs, setConfigs] = useState<ConfigResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const token = localStorage.getItem("df_token");

  // Redirect to login if no token — using component, not imperative navigate
  if (!token) {
    return <Navigate to="/admin/login" replace />;
  }

  const fetchStats = async () => {
    try {
      const data = await api.get<SystemStats>("/api/admin/stats");
      setStats(data);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        localStorage.removeItem("df_token");
        navigate("/admin/login", { replace: true });
      }
    }
  };

  const fetchRooms = async () => {
    setLoading(true);
    try {
      const data = await api.get<RoomSummary[]>("/api/admin/rooms");
      setRooms(data);
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    } finally {
      setLoading(false);
    }
  };

  const fetchConfigs = async () => {
    try {
      const data = await api.get<ConfigResponse[]>("/api/admin/configs");
      setConfigs(data);
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const destroyRoom = async (roomId: string) => {
    if (!confirm("确定要销毁这个空间吗？")) return;
    try {
      await api.post(`/api/admin/rooms/${roomId}/destroy`);
      fetchRooms();
      fetchStats();
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const updateConfig = async (key: string, value: string) => {
    try {
      await api.put(`/api/admin/configs/${key}`, { value });
      fetchConfigs();
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("df_token");
    navigate("/");
  };

  useEffect(() => {
    fetchStats();
    fetchRooms();
    fetchConfigs();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Top Nav */}
      <header className="border-b px-4 py-3 flex items-center justify-between sticky top-0 bg-background z-50">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="font-bold text-lg">DarkForest Admin</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={toggleTheme}>
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-1" />
            退出
          </Button>
        </div>
      </header>

      <div className="flex flex-col sm:flex-row">
        {/* Sidebar / Tabs */}
        <nav className="sm:w-56 border-b sm:border-b-0 sm:border-r sm:min-h-[calc(100vh-57px)] p-2 flex sm:flex-col gap-1 overflow-x-auto">
          {[
            { key: "dashboard" as Tab, icon: LayoutDashboard, label: "仪表盘" },
            { key: "rooms" as Tab, icon: DoorOpen, label: "空间管理" },
            { key: "config" as Tab, icon: Settings, label: "系统配置" },
          ].map(({ key, icon: Icon, label }) => (
            <Button
              key={key}
              variant={tab === key ? "secondary" : "ghost"}
              className="justify-start shrink-0"
              onClick={() => setTab(key)}
            >
              <Icon className="h-4 w-4 mr-2" />
              {label}
            </Button>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 p-4 sm:p-6 max-w-5xl">
          {error && (
            <div className="bg-destructive/10 text-destructive text-sm px-4 py-2 rounded-lg mb-4">
              {error}
            </div>
          )}

          {/* Dashboard */}
          {tab === "dashboard" && stats && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold">系统概览</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {[
                  { label: "总空间数", value: stats.total_rooms },
                  { label: "活跃空间", value: stats.active_rooms },
                  { label: "待销毁", value: stats.pending_destroy_rooms },
                  { label: "注册用户", value: stats.total_users },
                  { label: "今日消息", value: stats.total_messages_today },
                ].map(({ label, value }) => (
                  <Card key={label}>
                    <CardContent className="p-4 text-center">
                      <p className="text-2xl font-bold">{value}</p>
                      <p className="text-xs text-muted-foreground">{label}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Rooms */}
          {tab === "rooms" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">空间管理</h2>
                <Button variant="outline" size="sm" onClick={fetchRooms}>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  刷新
                </Button>
              </div>
              <div className="space-y-3">
                {rooms.map((room) => (
                  <Card key={room.id}>
                    <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{room.name}</span>
                          <Badge
                            variant={
                              room.status === "active"
                                ? "default"
                                : room.status === "pending_destroy"
                                ? "secondary"
                                : "outline"
                            }
                          >
                            {room.status === "active"
                              ? "活跃"
                              : room.status === "pending_destroy"
                              ? "待销毁"
                              : "已销毁"}
                          </Badge>
                        </div>
                        <div className="flex gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {room.online_count} 在线
                          </span>
                          <span>{room.message_count} 消息</span>
                          <span>IP: {room.creator_ip}</span>
                        </div>
                      </div>
                      {room.status !== "destroyed" && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => destroyRoom(room.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          销毁
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                ))}
                {rooms.length === 0 && !loading && (
                  <p className="text-center text-muted-foreground py-8">暂无空间</p>
                )}
              </div>
            </div>
          )}

          {/* Config */}
          {tab === "config" && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold">系统配置</h2>
              <div className="space-y-3">
                {configs.map((config) => (
                  <ConfigRow key={config.key} config={config} onSave={updateConfig} />
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function ConfigRow({
  config,
  onSave,
}: {
  config: ConfigResponse;
  onSave: (key: string, value: string) => void;
}) {
  const [value, setValue] = useState(config.value);
  return (
    <Card>
      <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">{config.key}</p>
          {config.description && (
            <p className="text-xs text-muted-foreground">{config.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="w-32"
          />
          <Button size="sm" onClick={() => onSave(config.key, value)}>
            保存
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
