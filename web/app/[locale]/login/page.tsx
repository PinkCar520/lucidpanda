'use client';

import React, { useState, useEffect } from 'react';
import { signIn, signOut, useSession } from 'next-auth/react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';

export default function LoginPage() {
  const t = useTranslations('Auth');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
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
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#020617] p-4">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-blue-400">
            {t('loginTitle')}
          </h1>
          <p className="text-slate-500 text-sm mt-2 font-mono uppercase tracking-widest">
            {t('identityTerminal')}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              {t('emailLabel')}
            </label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg py-3 px-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
              placeholder={t('emailPlaceholder')}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              {t('passwordLabel')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg py-3 px-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
              placeholder={t('passwordPlaceholder')}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition-all shadow-lg shadow-blue-500/20 ${
              loading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {loading ? t('authenticating') : t('signIn')}
          </button>
          <div className="text-right">
            <Link href="/forgot-password" locale={locale} className="text-sm text-blue-600 hover:text-blue-500 dark:text-emerald-500 dark:hover:text-emerald-400 font-medium">
              {t('forgotPassword')}
            </Link>
          </div>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('dontHaveAccount')}{' '}
            <Link href="/register" locale={locale} className="text-blue-600 hover:text-blue-500 dark:text-emerald-500 dark:hover:text-emerald-400 font-medium">
              {t('signUp')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
