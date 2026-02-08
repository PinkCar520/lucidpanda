'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Shield, KeyRound, Mail, AlertTriangle, Loader2, Monitor, Globe, Clock, Trash2, Smartphone, ShieldCheck, CheckCircle2, List } from 'lucide-react';
import Toast from '@/components/Toast';
import { authenticatedFetch } from '@/lib/api-client';

interface Session {
    id: number;
    device_info: { name?: string } | null;
    ip_address: string;
    created_at: string;
    last_active_at: string;
    is_current: boolean;
}

interface AuditLog {
    id: number;
    action: string;
    ip_address: string;
    user_agent: string;
    details: any;
    created_at: string;
}

export default function SecurityPage() {
  const t = useTranslations('Settings');
  const { data: sessionData, update } = useSession();
  
  // Password State
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordLoading, setPasswordLoading] = useState(false);

  // Email State
  const [emailForm, setEmailForm] = useState({
    newEmail: '',
    currentPassword: '',
  });
  const [emailLoading, setEmailLoading] = useState(false);

  // Phone State
  const [phoneForm, setPhoneForm] = useState({
    phoneNumber: '',
    code: '',
  });
  const [phoneLoading, setPhoneLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [phoneStep, setPhoneStep] = useState<'bind' | 'verify'>('bind');

  // 2FA State
  const [twoFASecret, setTwoFASecret] = useState<string | null>(null);
  const [qrCodeUrl, setQRCodeUrl] = useState<string | null>(null);
  const [twoFACode, setTwoFACode] = useState('');
  const [twoFALoading, setTwoFALoading] = useState(false);
  const [show2FASetup, setShow2FASetup] = useState(false);

  // Sessions State
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditLogsLoading, setAuditLogsLoading] = useState(false);

  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (sessionData) {
        fetchSessions();
        fetchAuditLogs();
    }
  }, [sessionData]);

  const fetchSessions = async () => {
    setSessionsLoading(true);
    try {
        const res = await authenticatedFetch('/api/v1/auth/sessions', sessionData);
        if (res.ok) {
            const data = await res.json();
            setSessions(data);
        }
    } catch (error) {
        console.error("Failed to fetch sessions", error);
    } finally {
        setSessionsLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
      setAuditLogsLoading(true);
      try {
          const res = await authenticatedFetch('/api/v1/auth/audit-log', sessionData);
          if (res.ok) {
              const data = await res.json();
              setAuditLogs(data);
          }
      } catch (error) {
          console.error("Failed to fetch audit logs", error);
      } finally {
          setAuditLogsLoading(false);
      }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setToast({ message: t('passwordsDoNotMatch'), type: 'error' });
      return;
    }

    setPasswordLoading(true);
    try {
      const res = await authenticatedFetch('/api/v1/auth/password/change', sessionData, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to change password');

      setToast({ message: t('passwordUpdated'), type: 'success' });
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
      fetchAuditLogs(); // Refresh logs
    } catch (error: any) {
      setToast({ message: error.message, type: 'error' });
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleEmailChangeRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailLoading(true);
    try {
      const res = await authenticatedFetch('/api/v1/auth/email/change-request', sessionData, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          new_email: emailForm.newEmail,
          current_password: emailForm.currentPassword,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to initiate email change');

      setToast({ message: t('verificationSent', { email: emailForm.newEmail }), type: 'success' });
      setEmailForm({ newEmail: '', currentPassword: '' });
      fetchAuditLogs();
    } catch (error: any) {
      setToast({ message: error.message, type: 'error' });
    } finally {
      setEmailLoading(false);
    }
  };

  const handleSendPhoneCode = async () => {
      setSendingCode(true);
      try {
          const res = await authenticatedFetch('/api/v1/auth/phone/request-verification', sessionData, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ phone_number: phoneForm.phoneNumber })
          });
          if (res.ok) {
              setPhoneStep('verify');
              setToast({ message: 'Code sent', type: 'success' });
          } else {
              const data = await res.json();
              throw new Error(data.detail || 'Failed to send code');
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      } finally {
          setSendingCode(false);
      }
  };

  const handleVerifyPhone = async (e: React.FormEvent) => {
      e.preventDefault();
      setPhoneLoading(true);
      try {
          const res = await authenticatedFetch('/api/v1/auth/phone/verify-binding', sessionData, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ phone_number: phoneForm.phoneNumber, code: phoneForm.code })
          });
          if (res.ok) {
              await update(); // Refresh session to get bound phone
              setToast({ message: 'Phone bound successfully', type: 'success' });
              setPhoneStep('bind');
              setPhoneForm({ phoneNumber: '', code: '' });
              fetchAuditLogs();
          } else {
              const data = await res.json();
              throw new Error(data.detail || 'Verification failed');
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      } finally {
          setPhoneLoading(false);
      }
  };

  const handleUnbindPhone = async () => {
      if (!confirm('Are you sure you want to unbind your phone?')) return;
      try {
          const res = await authenticatedFetch('/api/v1/auth/phone', sessionData, {
              method: 'DELETE'
          });
          if (res.ok) {
              await update();
              setToast({ message: 'Phone unbound successfully', type: 'success' });
              fetchAuditLogs();
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      }
  };

  const handleStart2FASetup = async () => {
      try {
          const res = await authenticatedFetch('/api/v1/auth/2fa/setup', sessionData, { method: 'POST' });
          if (res.ok) {
              const data = await res.json();
              setTwoFASecret(data.secret);
              setQRCodeUrl(data.qr_code_url);
              setShow2FASetup(true);
          }
      } catch (error) {
          console.error("Failed to start 2FA setup", error);
      }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
      e.preventDefault();
      setTwoFALoading(true);
      try {
          const res = await authenticatedFetch('/api/v1/auth/2fa/verify', sessionData, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ secret: twoFASecret, code: twoFACode })
          });
          if (res.ok) {
              await update();
              setToast({ message: t('twoFAEnabled'), type: 'success' });
              setShow2FASetup(false);
              setTwoFACode('');
              fetchAuditLogs();
          } else {
              const data = await res.json();
              throw new Error(data.detail || 'Verification failed');
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      } finally {
          setTwoFALoading(false);
      }
  };

  const handleDisable2FA = async () => {
      if (!confirm('Are you sure you want to disable 2FA? This will decrease your account security.')) return;
      try {
          const res = await authenticatedFetch('/api/v1/auth/2fa', sessionData, { method: 'DELETE' });
          if (res.ok) {
              await update();
              setToast({ message: t('twoFADisabled'), type: 'success' });
              fetchAuditLogs();
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      }
  };

  const handleRevokeSession = async (sessionId: number) => {
      try {
          const res = await authenticatedFetch(`/api/v1/auth/sessions/${sessionId}`, sessionData, {
              method: 'DELETE'
          });
          if (res.ok) {
              setSessions(sessions.filter(s => s.id !== sessionId));
              setToast({ message: t('sessionRevoked'), type: 'success' });
              fetchAuditLogs();
          } else {
              throw new Error('Failed to revoke session');
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      }
  };

  return (
    <div className="flex flex-col gap-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold">{t('security')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Manage your credentials and account security.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Change Password */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
            <KeyRound className="w-4 h-4 text-blue-500" />
            {t('changePassword')}
          </div>
          <Card className="p-6">
            <form onSubmit={handlePasswordChange} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('currentPassword')}</label>
                <input
                  type="password"
                  required
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                  className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('newPassword')}</label>
                <input
                  type="password"
                  required
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                  className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('confirmNewPassword')}</label>
                <input
                  type="password"
                  required
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                  className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={passwordLoading}
                className="mt-2 w-full py-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
              >
                {passwordLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {t('saveChanges')}
              </button>
            </form>
          </Card>
        </div>

        {/* Change Email */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
            <Mail className="w-4 h-4 text-emerald-500" />
            {t('changeEmail')}
          </div>
          <Card className="p-6 h-full flex flex-col justify-between">
            <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />
              <p className="text-[10px] text-amber-600 dark:text-amber-400 leading-relaxed">
                Changing your email requires verification of the new address. You will receive a link at the new address to confirm.
              </p>
            </div>
            <form onSubmit={handleEmailChangeRequest} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('newEmail')}</label>
                <input
                  type="email"
                  required
                  value={emailForm.newEmail}
                  onChange={(e) => setEmailForm({ ...emailForm, newEmail: e.target.value })}
                  className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Confirm with Password</label>
                <input
                  type="password"
                  required
                  value={emailForm.currentPassword}
                  onChange={(e) => setEmailForm({ ...emailForm, currentPassword: e.target.value })}
                  className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={emailLoading}
                className="mt-2 w-full py-2 bg-blue-600 dark:bg-emerald-500 text-white text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20"
              >
                {emailLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {t('initiateChange')}
              </button>
            </form>
          </Card>
        </div>

        {/* Phone Binding */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
            <Smartphone className="w-4 h-4 text-purple-500" />
            {t('phoneNumber')}
          </div>
          <Card className="p-6">
            {sessionData?.user?.phone_number ? (
                <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg">
                        <div className="flex items-center gap-3">
                            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                            <div>
                                <div className="text-sm font-bold">{sessionData.user.phone_number}</div>
                                <div className="text-[10px] text-slate-500 uppercase tracking-widest">Verified & Bound</div>
                            </div>
                        </div>
                        <button 
                            onClick={handleUnbindPhone}
                            className="text-xs font-bold text-red-500 hover:text-red-600 transition-colors"
                        >
                            {t('unbindPhone')}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col gap-4">
                    {phoneStep === 'bind' ? (
                        <div className="flex flex-col gap-4">
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('phoneNumber')}</label>
                                <div className="flex gap-2">
                                    <input
                                        type="tel"
                                        placeholder="+1234567890"
                                        value={phoneForm.phoneNumber}
                                        onChange={(e) => setPhoneForm({ ...phoneForm, phoneNumber: e.target.value })}
                                        className="flex-1 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                                    />
                                    <button 
                                        onClick={handleSendPhoneCode}
                                        disabled={sendingCode || !phoneForm.phoneNumber}
                                        className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-50 transition-all flex items-center gap-2"
                                    >
                                        {sendingCode && <Loader2 className="w-3 h-3 animate-spin" />}
                                        {t('sendCode')}
                                    </button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleVerifyPhone} className="flex flex-col gap-4 animate-in fade-in slide-in-from-right-2">
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('verificationCode')}</label>
                                <input
                                    type="text"
                                    required
                                    placeholder="Enter 6-digit code"
                                    value={phoneForm.code}
                                    onChange={(e) => setPhoneForm({ ...phoneForm, code: e.target.value })}
                                    className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                                />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    type="submit"
                                    disabled={phoneLoading}
                                    className="flex-1 py-2 bg-blue-600 dark:bg-emerald-500 text-white text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                                >
                                    {phoneLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                    {t('verifyAndBind')}
                                </button>
                                <button 
                                    type="button"
                                    onClick={() => setPhoneStep('bind')}
                                    className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs font-bold rounded-lg"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            )}
          </Card>
        </div>

        {/* 2FA Section */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            {t('twoFA')}
          </div>
          <Card className="p-6 h-full">
            {sessionData?.user?.is_two_fa_enabled ? (
                <div className="flex flex-col gap-4 h-full justify-center">
                    <div className="flex items-center justify-between p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                        <div className="flex items-center gap-3">
                            <ShieldCheck className="w-5 h-5 text-emerald-500" />
                            <div>
                                <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{t('status')}: {t('enabled')}</div>
                                <div className="text-[10px] text-slate-500 uppercase tracking-widest">Extra Security Active</div>
                            </div>
                        </div>
                        <button 
                            onClick={handleDisable2FA}
                            className="text-xs font-bold text-red-500 hover:text-red-600 transition-colors"
                        >
                            {t('disable2FA')}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col gap-4">
                    {!show2FASetup ? (
                        <div className="flex flex-col gap-4 h-full justify-between">
                            <p className="text-[10px] text-slate-500 leading-relaxed italic">
                                Add an extra layer of security to your account by requiring a code from your phone when you sign in.
                            </p>
                            <button 
                                onClick={handleStart2FASetup}
                                className="w-full py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-all flex items-center justify-center gap-2"
                            >
                                <KeyRound className="w-3.5 h-3.5" />
                                {t('setup2FA')}
                            </button>
                        </div>
                    ) : (
                        <form onSubmit={handleVerify2FA} className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-2">
                            <div className="flex flex-col items-center gap-4 py-2">
                                <div className="bg-white p-2 rounded-xl shadow-lg border border-slate-100">
                                    <img src={qrCodeUrl!} alt="2FA QR Code" className="w-32 h-32" />
                                </div>
                                <p className="text-[10px] text-center text-slate-500 leading-relaxed px-4">
                                    {t('scanQRCode')}
                                </p>
                                <div className="w-full h-px bg-slate-100 dark:bg-slate-800"></div>
                                <div className="flex flex-col gap-1.5 w-full">
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 text-center">{t('enterCodeFromApp')}</label>
                                    <input
                                        type="text"
                                        required
                                        maxLength={6}
                                        placeholder="000000"
                                        value={twoFACode}
                                        onChange={(e) => setTwoFACode(e.target.value)}
                                        className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm text-center font-mono tracking-[0.5em] focus:outline-none focus:border-blue-500 transition-colors"
                                    />
                                </div>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    type="submit"
                                    disabled={twoFALoading || twoFACode.length !== 6}
                                    className="flex-1 py-2 bg-blue-600 dark:bg-emerald-500 text-white text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    {twoFALoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                    {t('enable2FA')}
                                </button>
                                <button 
                                    type="button"
                                    onClick={() => setShow2FASetup(false)}
                                    className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs font-bold rounded-lg"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            )}
          </Card>
        </div>
      </div>

      {/* Active Sessions */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
            <Monitor className="w-4 h-4 text-indigo-500" />
            {t('activeSessions')}
        </div>
        <Card className="overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 dark:bg-slate-900/50 text-xs uppercase text-slate-500 font-bold tracking-wider">
                        <tr>
                            <th className="px-6 py-4">{t('device')}</th>
                            <th className="px-6 py-4">{t('location')} / {t('ipAddress')}</th>
                            <th className="px-6 py-4">{t('lastActive')}</th>
                            <th className="px-6 py-4 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {sessionsLoading ? (
                            <tr>
                                <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                                    Loading sessions...
                                </td>
                            </tr>
                        ) : sessions.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                                    No active sessions found.
                                </td>
                            </tr>
                        ) : (
                            sessions.map((sess) => (
                                <tr key={sess.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500">
                                                <Monitor className="w-4 h-4" />
                                            </div>
                                            <div>
                                                <div className="font-medium text-slate-900 dark:text-slate-100">
                                                    {sess.device_info?.name || 'Unknown Device'}
                                                </div>
                                                <div className="text-xs text-slate-500">
                                                    {sess.is_current ? t('currentSession') : 'Other Session'}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="font-medium text-slate-700 dark:text-slate-300">
                                                {sess.ip_address}
                                            </span>
                                            <span className="text-xs text-slate-500 flex items-center gap-1">
                                                <Globe className="w-3 h-3" />
                                                Unknown Location
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                                            <Clock className="w-3.5 h-3.5" />
                                            {new Date(sess.last_active_at || sess.created_at).toLocaleString()}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button 
                                            onClick={() => handleRevokeSession(sess.id)}
                                            className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 px-3 py-1.5 rounded text-xs font-bold transition-colors inline-flex items-center gap-1.5"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                            {t('revoke')}
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </Card>
      </div>

      {/* Security Audit Log */}
      <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
              <List className="w-4 h-4 text-blue-500" />
              {t('securityLog')}
          </div>
          <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                      <thead className="bg-slate-50 dark:bg-slate-900/50 text-xs uppercase text-slate-500 font-bold tracking-wider">
                          <tr>
                              <th className="px-6 py-4">{t('action')}</th>
                              <th className="px-6 py-4">{t('ipAddress')}</th>
                              <th className="px-6 py-4">{t('timestamp')}</th>
                              <th className="px-6 py-4">{t('details')}</th>
                          </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                          {auditLogsLoading ? (
                              <tr>
                                  <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                                      <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                                      Loading logs...
                                  </td>
                              </tr>
                          ) : auditLogs.length === 0 ? (
                              <tr>
                                  <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                                      {t('noAuditLogs')}
                                  </td>
                              </tr>
                          ) : (
                              auditLogs.map((log) => (
                                  <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors">
                                      <td className="px-6 py-4">
                                          <Badge variant={log.action.includes('FAILED') ? 'bullish' : 'neutral'} className="text-[10px]">
                                              {log.action}
                                          </Badge>
                                      </td>
                                      <td className="px-6 py-4 font-mono text-xs text-slate-500">{log.ip_address}</td>
                                      <td className="px-6 py-4 text-slate-500">{new Date(log.created_at).toLocaleString()}</td>
                                      <td className="px-6 py-4 text-xs text-slate-400 italic">
                                          {log.details ? JSON.stringify(log.details) : '-'}
                                      </td>
                                  </tr>
                              ))
                          )}
                      </tbody>
                  </table>
              </div>
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
