export interface UserDTO {
  id: string;
  email: string;
  username?: string;
  name?: string;
  nickname?: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  avatar_url?: string;
  is_two_fa_enabled: boolean;
}

export interface LoginResponseDTO {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserDTO;
  expires_in?: number;
}
