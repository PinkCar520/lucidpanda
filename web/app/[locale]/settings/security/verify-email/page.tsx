'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useRouter, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

export default function VerifyEmailPage() {
  const t = useTranslations('Settings');
  const searchParams = useSearchParams();
  const router = useRouter();
  const { locale } = useParams();
  const token = searchParams.get('token');

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Missing verification token.');
      return;
    }

    const verify = async () => {
      try {
        const res = await fetch('/api/v1/auth/email/verify-change', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        });

        const data = await res.json();
        if (res.ok) {
          setStatus('success');
          setMessage(t('emailVerified'));
          setTimeout(() => {
            router.push(`/${locale}/settings/profile`);
          }, 3000);
        } else {
          setStatus('error');
          setMessage(data.detail || 'Verification failed');
        }
      } catch (error) {
        setStatus('error');
        setMessage('Network error during verification');
      }
    };

    verify();
  }, [token, router, locale, t]);

  return (
    <div className="min-h-[400px] flex items-center justify-center">
      <Card className="max-w-md w-full p-8 flex flex-col items-center text-center gap-4">
        {status === 'loading' && (
          <>
            <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
            <h2 className="text-xl font-bold">Verifying your new email...</h2>
            <p className="text-sm text-slate-500">Please wait while we process your request.</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 className="w-12 h-12 text-emerald-500" />
            <h2 className="text-xl font-bold">Success!</h2>
            <p className="text-sm text-slate-500">{message}</p>
            <p className="text-xs text-slate-400 mt-2">Redirecting you to settings...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-12 h-12 text-rose-500" />
            <h2 className="text-xl font-bold">Verification Failed</h2>
            <p className="text-sm text-slate-500">{message}</p>
            <button
              onClick={() => router.push(`/${locale}/settings/security`)}
              className="mt-4 px-6 py-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-sm font-bold rounded-lg"
            >
              Back to Security
            </button>
          </>
        )}
      </Card>
    </div>
  );
}
