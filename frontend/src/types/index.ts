export interface Room {
  id: string;
  name: string;
  passcode: string;
  status: "active" | "pending_destroy" | "destroyed";
  max_members: number;
  timeout_minutes: number;
  last_activity_at: string;
  created_at: string;
  online_count: number;
}

export interface RoomSummary {
  id: string;
  name: string;
  status: string;
  creator_ip: string;
  passcode: string;
  online_count: number;
  message_count: number;
  last_activity_at: string;
  created_at: string;
}

export interface WSMessage {
  type: "message" | "system" | "join" | "leave" | "error" | "pong";
  content: string;
  nickname?: string | null;
  online_count?: number | null;
  timestamp?: string | null;
}

export interface MessageResponse {
  id: string;
  room_id: string;
  content: string;
  nickname: string;
  created_at: string;
}

export interface SystemStats {
  total_rooms: number;
  active_rooms: number;
  pending_destroy_rooms: number;
  total_users: number;
  total_messages_today: number;
}

export interface ConfigResponse {
  key: string;
  value: string;
  description: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  nickname: string | null;
  role: string;
  is_active: boolean;
}

export interface UserCreateRequest {
  username: string;
  email: string;
  password: string;
  nickname: string | null;
  role: "admin" | "user";
  is_active: boolean;
}

export interface UserUpdateRequest {
  email: string;
  nickname: string | null;
  role: "admin" | "user";
  is_active: boolean;
}
