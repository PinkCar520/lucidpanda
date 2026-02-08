'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { User, Mail, Calendar, ShieldCheck, Loader2 } from 'lucide-react';
import Toast from '@/components/Toast';

export default function ProfilePage() {
  const t = useTranslations('Settings');
  const { data: session, update } = useSession();
  
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (session?.user?.name) {
      setFullName(session.user.name);
    }
  }, [session]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch('/api/v1/auth/me', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ full_name: fullName }),
      });

      if (!res.ok) {
        throw new Error('Failed to update profile');
      }

      const updatedUser = await res.json();
      
      // Update NextAuth session
      await update({
        ...session,
        user: {
          ...session?.user,
          name: updatedUser.full_name,
        },
      });

      setToast({ message: t('saveChanges'), type: 'success' });
    } catch (error) {
      setToast({ message: 'Error updating profile', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  if (!session) return null;

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold">{t('basicInfo')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Manage your public identity on AlphaSignal.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Card */}
        <Card className="lg:col-span-1 flex flex-col items-center text-center p-8">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center text-white text-3xl font-black mb-4 shadow-xl shadow-blue-500/20">
            {session.user?.name?.[0]?.toUpperCase() || session.user?.email?.[0]?.toUpperCase()}
          </div>
          <h3 className="text-lg font-bold">{session.user?.name || 'Anonymous'}</h3>
          <p className="text-xs text-slate-500 font-mono mb-4">{session.user?.email}</p>
          <Badge variant="neutral" className="uppercase tracking-widest text-[10px]">
            {session.user?.role || 'User'}
          </Badge>
          
          <div className="w-full border-t border-slate-100 dark:border-slate-800 mt-6 pt-6 flex flex-col gap-3">
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>Identity Verified</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <Calendar className="w-4 h-4" />
              <span>Member since Feb 2026</span>
            </div>
          </div>
        </Card>

        {/* Edit Form */}
        <Card className="lg:col-span-2 p-6">
          <form onSubmit={handleUpdateProfile} className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {t('fullName')}
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                  placeholder="Enter your full name"
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  value={session.user?.email || ''}
                  disabled
                  className="w-full bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-500 cursor-not-allowed"
                />
              </div>
              <p className="text-[10px] text-slate-400 italic">
                Email can be changed in the Security section.
              </p>
            </div>

            <div className="pt-4 flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 dark:bg-emerald-500 text-white text-sm font-bold rounded-lg hover:opacity-90 transition-opacity shadow-lg shadow-blue-500/20 flex items-center gap-2"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? t('changing') : t('saveChanges')}
              </button>
            </div>
          </form>
        </Card>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
