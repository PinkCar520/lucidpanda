'use client';

import React, { useState, useEffect } from 'react';
import { signIn, signOut, useSession } from 'next-auth/react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { Fingerprint, Loader2 } from 'lucide-react';
import { authenticatePasskey } from '@/lib/passkey';

export default function LoginPage() {
  const t = useTranslations('Auth');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [passkeyLoading, setPasskeyLoading] = useState(false);
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const locale = params.locale as string;
  const { data: session } = useSession();

  // Check for errors from URL (like session_expired)
  useEffect(() => {
    const errorParam = searchParams.get('error');
    if (errorParam === 'session_expired' || errorParam === 'RefreshAccessTokenError') {
      setError(t('sessionExpired'));
    }
  }, [searchParams, t]);

  // If there's an error in the session, clear it
  useEffect(() => {
    if (session && (session as any).error) {
      console.log("[Login] Session error detected, signing out to clear state:", (session as any).error);
      signOut({ redirect: false });
    }
  }, [session]);

  const handlePasskeyLogin = async () => {
    setPasskeyLoading(true);
    setError('');
    try {
      const authResult = await authenticatePasskey();

      const result = await signIn('credentials', {
        auth_data: JSON.stringify(authResult.auth_data),
        state: authResult.state,
        action: 'passkey',
        redirect: false,
      });

      if (result?.error) {
        setError(t('passkeyLoginFailed'));
      } else {
        router.push(`/${locale}`);
        router.refresh();
      }
    } catch (err: any) {
      if (err.name !== 'NotAllowedError') {
        setError(err.message || t('passkeyLoginFailed'));
      }
    } finally {
      setPasskeyLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError(t('invalidEmailPassword'));
      } else {
        router.push(`/${locale}`);
        router.refresh();
      }
    } catch (err) {
      setError(t('unexpectedError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#020617] p-4 md:p-6">
      <div className="w-full max-w-[720px] bg-white dark:bg-slate-900 rounded-[2rem] md:rounded-3xl shadow-xl shadow-slate-200/50 dark:shadow-black/40 border border-slate-200/70 dark:border-slate-800 p-6 md:p-12">
        <div className="text-center mb-6 md:mb-10">
          <h1 className="text-2xl md:text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-blue-400">
            {t('loginTitle')}
          </h1>
          <p className="text-slate-500 text-[10px] md:text-sm mt-1.5 font-mono uppercase tracking-widest">
            {t('identityTerminal')}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-6 md:gap-10 items-start md:items-center">
          {/* Left column: email/password */}
          <form onSubmit={handleSubmit} className="space-y-4 md:space-y-6">
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 ml-1">
                {t('emailLabel')}
              </label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                placeholder={t('emailPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 ml-1">
                {t('passwordLabel')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                placeholder={t('passwordPlaceholder')}
              />
              <div className="mt-2 ml-1">
                <Link
                  href="/forgot-password"
                  locale={locale}
                  className="text-xs text-blue-600 hover:text-blue-500 dark:text-emerald-500 dark:hover:text-emerald-400 font-medium"
                >
                  {t('forgotPassword')}
                </Link>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 rounded-xl md:rounded-3xl transition-all shadow-lg shadow-blue-500/20 text-sm md:text-base ${loading ? 'opacity-50 cursor-not-allowed' : ''
                }`}
            >
              {loading ? t('authenticating') : t('signIn')}
            </button>

            <p className="text-xs md:text-sm text-slate-500 dark:text-slate-400 text-center md:text-left">
              {t('dontHaveAccount')}{' '}
              <Link href="/register" locale={locale} className="text-blue-600 hover:text-blue-500 dark:text-emerald-500 dark:hover:text-emerald-400 font-bold">
                {t('signUp')}
              </Link>
            </p>
          </form>

          {/* Center divider */}
          <div className="flex md:h-full items-center justify-center py-2 md:py-0">
            <div className="w-full h-px md:w-px md:h-28 rounded-full bg-slate-100 dark:bg-slate-800" />
          </div>

          {/* Right column: Passkey elevated */}
          <div className="space-y-4 self-center">
            <div className="rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-5 md:p-6 shadow-sm">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-4">
                {t('orContinueWith')}
              </p>
              <button
                type="button"
                onClick={handlePasskeyLogin}
                disabled={passkeyLoading || loading}
                className="w-full bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-900 dark:text-white font-bold py-3 md:py-4 px-3 rounded-xl transition-all flex items-center justify-center gap-2 md:gap-3 border border-slate-200 dark:border-slate-700 shadow-sm whitespace-nowrap text-sm md:text-base"
              >
                {passkeyLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Fingerprint className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                )}
                <span className="truncate">{t('signInWithPasskey')}</span>
              </button>
              <p className="text-[10px] md:text-xs text-slate-400 dark:text-slate-500 mt-3 leading-relaxed">
                Use your device-backed passkey for faster, phishing-resistant sign-in.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

  );
}
