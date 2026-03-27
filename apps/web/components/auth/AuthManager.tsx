"use client"

import * as React from "react"
import { useSession, signIn, signOut } from "next-auth/react"
import { subscribeReauth, processQueue, setRefreshing } from "@/lib/auth-events"
import { atomicSignOut } from "@/lib/auth-cleanup"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/Dialog"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"
import { Lock, LogOut, RefreshCw } from "lucide-react"
import { useTranslations } from "next-intl"

export function AuthManager({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession()
  const [showModal, setShowModal] = React.useState(false)
  const [password, setPassword] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const t = useTranslations("Auth")

  // Use a broadcast channel for multi-tab sync
  const channel = React.useMemo(() => {
    if (typeof window === "undefined") return null
    return new BroadcastChannel("auth_sync")
  }, [])

  React.useEffect(() => {
    if (!channel) return

    channel.onmessage = (event) => {
      if (event.data.type === "SESSION_REVIVED") {
        console.log("[AuthManager] Session revived in another tab, syncing...")
        setShowModal(false)
        setRefreshing(false)
        // NextAuth will naturally pick up the new cookie on next check
      }
    }

    return () => channel.close()
  }, [channel])

  React.useEffect(() => {
    const unsubscribe = subscribeReauth(() => {
      setShowModal(true)
    })
    return unsubscribe
  }, [])

  const handleReauth = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const email = session?.user?.email || session?.user?.username
      if (!email) throw new Error("No user identifier found")

      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      })

      if (result?.error) {
        setError(t("invalidEmailPassword"))
      } else {
        // Success!
        const { getSession } = await import("next-auth/react")
        const newSession = await getSession()
        
        if (newSession?.accessToken) {
          console.log("[AuthManager] Re-authentication successful.")
          processQueue(newSession.accessToken)
          
          // Notify other tabs
          channel?.postMessage({ type: "SESSION_REVIVED" })
          
          setShowModal(false)
          setPassword("")
        } else {
          setError(t("unexpectedError"))
        }
      }
    } catch (err) {
      setError(t("unexpectedError"))
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = () => {
    const locale = window.location.pathname.split('/')[1] || 'en';
    atomicSignOut(locale);
  }

  return (
    <>
      {children}
      
      <Dialog open={showModal} onOpenChange={(open) => !isLoading && setShowModal(open)}>
        <DialogContent className="sm:max-w-md bg-slate-900/90 backdrop-blur-xl border-slate-800 shadow-2xl z-[200]">
          <DialogHeader className="items-center text-center">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center mb-2">
              <Lock className="w-6 h-6 text-blue-500" />
            </div>
            <DialogTitle className="text-xl font-black tracking-tight">{t("sessionExpiredTitle") || "Session Expired"}</DialogTitle>
            <DialogDescription className="text-slate-400">
              {t("sessionExpiredDesc") || "Please enter your password to continue without losing your data."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleReauth} className="space-y-4 py-4">
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Identity</div>
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50 text-sm font-medium text-slate-200 truncate">
                {session?.user?.name || session?.user?.email}
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">{t("passwordLabel")}</div>
              <Input
                type="password"
                placeholder="••••••••"
                className="bg-slate-950/50 border-slate-700 focus:border-blue-500 transition-all"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
                required
              />
              {error && <p className="text-xs text-rose-500 font-medium px-1 animate-in fade-in slide-in-from-top-1">{error}</p>}
            </div>

            <div className="flex flex-col gap-2 pt-2">
              <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold h-11" disabled={isLoading}>
                {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : t("confirmWithPassword") || "Verify Password"}
              </Button>
              <Button type="button" variant="ghost" className="w-full text-slate-500 hover:text-slate-200" onClick={handleLogout} disabled={isLoading}>
                <LogOut className="w-4 h-4 mr-2" />
                {t("signOut")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
