import { useState, useEffect } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import {
  LayoutDashboard,
  Archive,
  DoorOpen,
  Settings,
  Users,
  UserPlus,
  Pencil,
  KeyRound,
  Trash2,
  RefreshCw,
  RotateCcw,
  ArrowLeft,
  Eye,
  MessageSquareText,
  Moon,
  Sun,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useTheme } from "@/hooks/useTheme";
import { api, ApiError } from "@/lib/api";
import type {
  RoomSummary,
  SystemStats,
  ConfigResponse,
  MessageResponse,
  UserCreateRequest,
  UserResponse,
  UserUpdateRequest,
} from "@/types";

type Tab = "dashboard" | "rooms" | "users" | "config";
type RoomStatusTab = "active" | "pending";
type UserFormState = {
  username: string;
  email: string;
  password: string;
  nickname: string;
  role: "admin" | "user";
  is_active: boolean;
};

const emptyUserForm: UserFormState = {
  username: "",
  email: "",
  password: "",
  nickname: "",
  role: "user",
  is_active: true,
};

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [roomStatusTab, setRoomStatusTab] = useState<RoomStatusTab>("active");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [rooms, setRooms] = useState<RoomSummary[]>([]);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [messageRoom, setMessageRoom] = useState<RoomSummary | null>(null);
  const [messageDialogOpen, setMessageDialogOpen] = useState(false);
  const [configs, setConfigs] = useState<ConfigResponse[]>([]);
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [userForm, setUserForm] = useState<UserFormState>(emptyUserForm);
  const [editingUser, setEditingUser] = useState<UserResponse | null>(null);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [passwordUser, setPasswordUser] = useState<UserResponse | null>(null);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [newPassword, setNewPassword] = useState("");
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

  const fetchUsers = async () => {
    try {
      const data = await api.get<UserResponse[]>("/api/admin/users");
      setUsers(data);
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const viewMessages = async (room: RoomSummary) => {
    setError("");
    try {
      const data = await api.get<MessageResponse[]>(
        `/api/admin/rooms/${room.id}/messages?limit=100`
      );
      setMessageRoom(room);
      setMessages(data);
      setMessageDialogOpen(true);
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const archiveRoom = async (roomId: string) => {
    if (!confirm("确定要归档这个空间吗？归档后会进入待销毁列表。")) return;
    try {
      await api.post(`/api/admin/rooms/${roomId}/archive`);
      await fetchRooms();
      await fetchStats();
      if (messageRoom?.id === roomId) {
        setMessageRoom((room) => (room ? { ...room, status: "pending_destroy" } : room));
      }
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const destroyRoom = async (roomId: string) => {
    if (!confirm("确定要彻底销毁这个空间吗？空间和对话数据都会从数据库删除。")) return;
    try {
      await api.post(`/api/admin/rooms/${roomId}/destroy`);
      await fetchRooms();
      await fetchStats();
      if (messageRoom?.id === roomId) {
        setMessageDialogOpen(false);
        setMessageRoom(null);
        setMessages([]);
      }
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const restoreRoom = async (roomId: string) => {
    try {
      await api.post(`/api/admin/rooms/${roomId}/restore`);
      await fetchRooms();
      await fetchStats();
      if (messageRoom?.id === roomId) {
        setMessageRoom((room) => (room ? { ...room, status: "active" } : room));
      }
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

  const openCreateUser = () => {
    setEditingUser(null);
    setUserForm(emptyUserForm);
    setUserDialogOpen(true);
  };

  const openEditUser = (user: UserResponse) => {
    setEditingUser(user);
    setUserForm({
      username: user.username,
      email: user.email,
      password: "",
      nickname: user.nickname || "",
      role: user.role === "admin" ? "admin" : "user",
      is_active: user.is_active,
    });
    setUserDialogOpen(true);
  };

  const saveUser = async () => {
    setError("");
    try {
      if (editingUser) {
        const payload: UserUpdateRequest = {
          email: userForm.email,
          nickname: userForm.nickname || null,
          role: userForm.role,
          is_active: userForm.is_active,
        };
        await api.put<UserResponse>(`/api/admin/users/${editingUser.id}`, payload);
      } else {
        const payload: UserCreateRequest = {
          username: userForm.username,
          email: userForm.email,
          password: userForm.password,
          nickname: userForm.nickname || null,
          role: userForm.role,
          is_active: userForm.is_active,
        };
        await api.post<UserResponse>("/api/admin/users", payload);
      }
      setUserDialogOpen(false);
      await fetchUsers();
      await fetchStats();
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const openPasswordDialog = (user: UserResponse) => {
    setPasswordUser(user);
    setNewPassword("");
    setPasswordDialogOpen(true);
  };

  const savePassword = async () => {
    if (!passwordUser) return;
    setError("");
    try {
      await api.put<UserResponse>(`/api/admin/users/${passwordUser.id}/password`, {
        password: newPassword,
      });
      setPasswordDialogOpen(false);
    } catch (e) {
      if (e instanceof ApiError) setError(e.detail);
    }
  };

  const deleteUser = async (user: UserResponse) => {
    if (!confirm(`确定要删除用户 ${user.username} 吗？`)) return;
    setError("");
    try {
      await api.del(`/api/admin/users/${user.id}`);
      await fetchUsers();
      await fetchStats();
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
    fetchUsers();
  }, []);

  const activeRooms = rooms.filter((room) => room.status === "active");
  const pendingRooms = rooms.filter((room) => room.status !== "active");
  const visibleRooms = roomStatusTab === "active" ? activeRooms : pendingRooms;

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
            { key: "users" as Tab, icon: Users, label: "用户管理" },
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
        <main className="min-w-0 flex-1 p-4 sm:p-6">
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
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-xl font-bold">空间管理</h2>
                <div className="flex items-center gap-2">
                  <div className="rounded-md border bg-muted/30 p-1">
                    {[
                      { key: "active" as RoomStatusTab, label: `活跃 ${activeRooms.length}` },
                      { key: "pending" as RoomStatusTab, label: `待销毁 ${pendingRooms.length}` },
                    ].map((item) => (
                      <Button
                        key={item.key}
                        variant={roomStatusTab === item.key ? "secondary" : "ghost"}
                        size="sm"
                        className="h-8"
                        onClick={() => setRoomStatusTab(item.key)}
                      >
                        {item.label}
                      </Button>
                    ))}
                  </div>
                  <Button variant="outline" size="icon" onClick={fetchRooms} title="刷新">
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {visibleRooms.map((room) => (
                  <Card key={room.id} className="overflow-hidden">
                    <CardContent className="space-y-3 p-4">
                      <div className="flex min-h-7 items-start justify-between gap-3">
                        <span className="min-w-0 break-words font-semibold leading-7">
                          {room.name}
                        </span>
                        <Badge
                          variant={
                            room.status === "active"
                              ? "default"
                              : room.status === "pending_destroy"
                              ? "secondary"
                              : "outline"
                          }
                          className="shrink-0"
                        >
                          {room.status === "active"
                            ? "活跃"
                            : room.status === "pending_destroy"
                            ? "待销毁"
                            : "已销毁"}
                        </Badge>
                      </div>
                      <div className="rounded-md bg-muted/60 px-3 py-2 font-mono text-sm">
                        {room.passcode}
                      </div>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                          <Users className="h-3.5 w-3.5" />
                          {room.online_count} 在线
                        </span>
                        <span>{room.message_count} 消息</span>
                        <span>IP: {room.creator_ip}</span>
                      </div>
                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button variant="outline" size="sm" onClick={() => viewMessages(room)}>
                          <Eye className="mr-1 h-4 w-4" />
                          查看
                        </Button>
                        {room.status !== "active" && (
                          <Button variant="secondary" size="sm" onClick={() => restoreRoom(room.id)}>
                            <RotateCcw className="mr-1 h-4 w-4" />
                            恢复
                          </Button>
                        )}
                        {room.status === "active" ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => archiveRoom(room.id)}
                          >
                            <Archive className="mr-1 h-4 w-4" />
                            归档
                          </Button>
                        ) : (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => destroyRoom(room.id)}
                          >
                            <Trash2 className="mr-1 h-4 w-4" />
                            销毁
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {visibleRooms.length === 0 && !loading && (
                  <p className="col-span-full text-center text-muted-foreground py-8">暂无空间</p>
                )}
              </div>

              <Dialog open={messageDialogOpen} onOpenChange={setMessageDialogOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <MessageSquareText className="h-5 w-5" />
                      {messageRoom?.name || "空间"} 的对话内容
                    </DialogTitle>
                    <DialogDescription>
                      口令 {messageRoom?.passcode || "-"} · 最近 {messages.length} 条消息
                    </DialogDescription>
                  </DialogHeader>
                  <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
                    {messages.map((message) => (
                      <div key={message.id} className="rounded-md border bg-muted/30 px-3 py-2">
                        <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <span className="font-medium text-foreground">{message.nickname}</span>
                          <span>{new Date(message.created_at).toLocaleString()}</span>
                        </div>
                        <p className="break-words text-sm">{message.content}</p>
                      </div>
                    ))}
                    {messages.length === 0 && (
                      <p className="text-center text-sm text-muted-foreground py-6">暂无对话内容</p>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}

          {/* Users */}
          {tab === "users" && (
            <div className="space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-xl font-bold">用户管理</h2>
                <div className="flex gap-2">
                  <Button variant="outline" size="icon" onClick={fetchUsers} title="刷新">
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                  <Button size="sm" onClick={openCreateUser}>
                    <UserPlus className="mr-1 h-4 w-4" />
                    新增用户
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {users.map((user) => (
                  <Card key={user.id} className="overflow-hidden">
                    <CardContent className="space-y-3 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="break-words font-semibold leading-7">{user.username}</p>
                          <p className="break-words text-xs text-muted-foreground">{user.email}</p>
                        </div>
                        <Badge variant={user.is_active ? "default" : "outline"} className="shrink-0">
                          {user.is_active ? "启用" : "停用"}
                        </Badge>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span>昵称: {user.nickname || "-"}</span>
                        <span>角色: {user.role === "admin" ? "管理员" : "普通用户"}</span>
                      </div>
                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button variant="outline" size="sm" onClick={() => openEditUser(user)}>
                          <Pencil className="mr-1 h-4 w-4" />
                          修改
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => openPasswordDialog(user)}>
                          <KeyRound className="mr-1 h-4 w-4" />
                          密码
                        </Button>
                        <Button variant="destructive" size="sm" onClick={() => deleteUser(user)}>
                          <Trash2 className="mr-1 h-4 w-4" />
                          删除
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {users.length === 0 && (
                  <p className="col-span-full text-center text-muted-foreground py-8">暂无用户</p>
                )}
              </div>

              <Dialog open={userDialogOpen} onOpenChange={setUserDialogOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>{editingUser ? "修改用户" : "新增用户"}</DialogTitle>
                    <DialogDescription>
                      {editingUser ? "修改用户资料、状态和角色" : "创建后台用户并分配角色"}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="space-y-1 text-sm">
                      <span>用户名</span>
                      <Input
                        value={userForm.username}
                        disabled={Boolean(editingUser)}
                        onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                      />
                    </label>
                    <label className="space-y-1 text-sm">
                      <span>邮箱</span>
                      <Input
                        value={userForm.email}
                        onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                      />
                    </label>
                    {!editingUser && (
                      <label className="space-y-1 text-sm">
                        <span>密码</span>
                        <Input
                          type="password"
                          value={userForm.password}
                          onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                        />
                      </label>
                    )}
                    <label className="space-y-1 text-sm">
                      <span>昵称</span>
                      <Input
                        value={userForm.nickname}
                        onChange={(e) => setUserForm({ ...userForm, nickname: e.target.value })}
                      />
                    </label>
                    <label className="space-y-1 text-sm">
                      <span>角色</span>
                      <select
                        value={userForm.role}
                        onChange={(e) =>
                          setUserForm({ ...userForm, role: e.target.value as "admin" | "user" })
                        }
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      >
                        <option value="user">普通用户</option>
                        <option value="admin">管理员</option>
                      </select>
                    </label>
                    <label className="flex items-center gap-2 pt-7 text-sm">
                      <input
                        type="checkbox"
                        checked={userForm.is_active}
                        onChange={(e) => setUserForm({ ...userForm, is_active: e.target.checked })}
                        className="h-4 w-4"
                      />
                      启用账号
                    </label>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setUserDialogOpen(false)}>
                      取消
                    </Button>
                    <Button onClick={saveUser}>保存</Button>
                  </div>
                </DialogContent>
              </Dialog>

              <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>修改密码</DialogTitle>
                    <DialogDescription>
                      为用户 {passwordUser?.username || "-"} 设置新密码
                    </DialogDescription>
                  </DialogHeader>
                  <label className="space-y-1 text-sm">
                    <span>新密码</span>
                    <Input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                  </label>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setPasswordDialogOpen(false)}>
                      取消
                    </Button>
                    <Button onClick={savePassword}>保存</Button>
                  </div>
                </DialogContent>
              </Dialog>
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
