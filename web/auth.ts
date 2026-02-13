import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { API_INTERNAL_URL as API_URL } from "@/lib/constants";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "AlphaSignal",
      credentials: {
        email: { label: "Email or Username", type: "text" },
        password: { label: "Password", type: "password" },
        // Add hidden fields for WebAuthn/Passkeys to satisfy TypeScript
        action: { type: "text" },
        auth_data: { type: "text" },
        state: { type: "text" },
      },
      async authorize(credentials) {
        if (!credentials) return null;
        
        // Cast to any to access dynamic Passkey fields safely
        const creds = credentials as any;

        try {
          let res;
          if (creds.action === 'passkey') {
            // WebAuthn Passkey Login
            res = await fetch(`${API_URL}/api/v1/auth/passkeys/login/verify`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                auth_data: creds.auth_data,
                state: creds.state,
              }),
            });
          } else {
            // Traditional Password Login
            if (!creds.email || !creds.password) return null;
            
            const formData = new URLSearchParams();
            formData.append("username", creds.email as string);
            formData.append("password", creds.password as string);

            res = await fetch(`${API_URL}/api/v1/auth/login`, {
              method: "POST",
              body: formData,
              headers: { "Content-Type": "application/x-www-form-urlencoded" },
            });
          }

          const data = await res.json();

          if (res.ok && data.access_token) {
            return {
              id: data.user.id,
              email: data.user.email,
              username: data.user.username,
              name: data.user.name || data.user.full_name,
              role: data.user.role,
              avatar_url: data.user.avatar_url,
              nickname: data.user.nickname,
              gender: data.user.gender,
              birthday: data.user.birthday,
              location: data.user.location,
              language_preference: data.user.language_preference,
              timezone: data.user.timezone,
              theme_preference: data.user.theme_preference,
              phone_number: data.user.phone_number,
              is_phone_verified: data.user.is_phone_verified,
              is_two_fa_enabled: data.user.is_two_fa_enabled,
              created_at: data.user.created_at,
              username_updated_at: data.user.username_updated_at,
              accessToken: data.access_token,
              refreshToken: data.refresh_token,
              accessTokenExpires: Date.now() + data.expires_in * 1000,
            };
          }
          return null;
        } catch (error) {
          console.error("Auth Error:", error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, account, trigger, session }) {
      // Initial sign in
      if (user && account) {
        return {
          accessToken: user.accessToken,
          refreshToken: user.refreshToken,
          accessTokenExpires: user.accessTokenExpires,
          user: {
            id: user.id,
            email: user.email!,
            username: user.username,
            name: user.name,
            role: user.role!,
            avatar_url: user.avatar_url,
            nickname: user.nickname,
            gender: user.gender,
            birthday: user.birthday,
            location: user.location,
            language_preference: user.language_preference,
            timezone: user.timezone,
            theme_preference: user.theme_preference,
            phone_number: user.phone_number,
            is_phone_verified: user.is_phone_verified,
            is_two_fa_enabled: user.is_two_fa_enabled,
            created_at: user.created_at,
            username_updated_at: user.username_updated_at,
          },
        };
      }

      // Handle session update
      if (trigger === "update" && session?.user) {
        console.log("[AUTH] JWT Update Triggered:", session.user);
        const newToken = {
          ...token,
          user: {
            ...(token.user as any),
            ...session.user,
          }
        };
        // If we are updating the session, we should probably clear any error
        delete (newToken as any).error;
        return newToken;
      }

      // Return previous token if the access token has not expired yet
      // Use a 30-second buffer to avoid race conditions near expiry
      if (Date.now() < (token.accessTokenExpires as number) - 30000) {
        return token;
      }

      // Access token has expired or is about to expire, try to update it
      console.log("[AUTH] Access Token expired or near expiry, rotating...");
      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      if (token && token.user) {
        session.user = {
          ...session.user,
          ...token.user,
        };
        session.accessToken = token.accessToken as string;
        if (token.error) {
          (session as any).error = token.error;
        }
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
});

async function refreshAccessToken(token: any) {
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    });

    const refreshedTokens = await res.json();

    if (!res.ok) {
      throw refreshedTokens;
    }

    return {
      ...token,
      accessToken: refreshedTokens.access_token,
      accessTokenExpires: Date.now() + refreshedTokens.expires_in * 1000,
      refreshToken: refreshedTokens.refresh_token ?? token.refreshToken, // Fallback to old refresh token
    };
  } catch (error) {
    console.error("RefreshAccessTokenError", error);
    return {
      ...token,
      error: "RefreshAccessTokenError",
    };
  }
}
