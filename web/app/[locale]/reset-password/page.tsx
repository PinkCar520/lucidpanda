'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';

export default function ResetPasswordPage() {
  const t = useTranslations('Auth');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const locale = params.locale as string;

  useEffect(() => {
    const tokenFromUrl = searchParams.get('token');
    if (tokenFromUrl) {
      setToken(tokenFromUrl);
    } else {
      setError(t('tokenMissing'));
    }
  }, [searchParams, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setError('');

    if (!token) {
      setError(t('tokenNotFound'));
      setLoading(false);
      return;
    }

    if (password !== confirmPassword) {
      setError(t('passwordsDoNotMatch'));
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setError(t('passwordMinLength'));
      setLoading(false);
      return;
    }

    try {
      const res = await fetch('/api/v1/auth/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token, new_password: password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail ? data.detail[0]?.msg || data.detail : data.message || t('resetFailed'));
        return;
      }

      setMessage(data.message || t('resetSuccessful'));
      // Optionally redirect to login page after a short delay
      setTimeout(() => {
        router.push(`/${locale}/login`);
      }, 3000);

    } catch (err) {
      setError(t('networkError'));
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
            {t('resetPasswordTitle')}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {message && (
          <div className="mb-6 p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-600 dark:text-emerald-400 text-sm">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              {t('newPasswordLabel')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg py-3 px-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
              placeholder={t('passwordPlaceholderRegister')}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              {t('confirmPasswordLabel')}
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg py-3 px-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
              placeholder={t('passwordPlaceholder')}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !token}
            className={`w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition-all shadow-lg shadow-blue-500/20 ${
              loading || !token ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {loading ? t('resetting') : t('resetPasswordTitle')}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('rememberPassword')}{' '}
            <Link href="/login" locale={locale} className="text-blue-600 hover:text-blue-500 dark:text-emerald-500 dark:hover:text-emerald-400 font-medium">
              {t('signIn')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
