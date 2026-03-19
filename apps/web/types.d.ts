declare module 'react-plotly.js';

import "next-auth";
import { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface User {
    id: string;
    username?: string | null;
    role?: string;
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpires?: number;
    avatar_url?: string | null;
    nickname?: string | null;
    gender?: string | null;
    birthday?: string | null;
    location?: string | null;
    language_preference?: string | null;
    timezone?: string | null;
    theme_preference?: string | null;
    phone_number?: string | null;
    is_phone_verified?: boolean;
    is_two_fa_enabled?: boolean;
    created_at?: string;
    username_updated_at?: string | null;
  }

  interface Session {
    accessToken?: string;
    user: {
      id: string;
      username?: string | null;
      role: string;
      avatar_url?: string | null;
      nickname?: string | null;
      gender?: string | null;
      birthday?: string | null;
      location?: string | null;
      language_preference?: string | null;
      timezone?: string | null;
      theme_preference?: string | null;
      phone_number?: string | null;
      is_phone_verified?: boolean;
      is_two_fa_enabled?: boolean;
      created_at?: string;
      username_updated_at?: string | null;
    } & DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpires?: number;
    user?: {
      id: string;
      email: string;
      username?: string | null;
      name?: string | null;
      role: string;
      avatar_url?: string | null;
      nickname?: string | null;
      gender?: string | null;
      birthday?: string | null;
      location?: string | null;
      language_preference?: string | null;
      timezone?: string | null;
      theme_preference?: string | null;
      phone_number?: string | null;
      is_phone_verified?: boolean;
      is_two_fa_enabled?: boolean;
      created_at?: string;
      username_updated_at?: string | null;
    };
  }
}
