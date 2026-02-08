declare module 'react-plotly.js';

import "next-auth";
import { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface User {
    id: string;
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
  }

  interface Session {
    accessToken?: string;
    user: {
      id: string;
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
    };
  }
}
