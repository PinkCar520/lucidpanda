'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { 
    Dialog, DialogContent, DialogHeader, 
    DialogTitle, DialogTrigger, DialogDescription, DialogFooter 
} from '@/components/ui/Dialog';
import { 
    Shield, KeyRound, Loader2, 
    Monitor, Globe, Clock, Trash2, ShieldCheck,
    Fingerprint, Lock, MailCheck, ShieldAlert, List, ChevronRight
} from 'lucide-react';
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
  const [isPasswordDialogOpen, setIsPasswordPasswordDialogOpen] = useState(false);

  // Identity (Email/Phone) State
  const [isIdentityDialogOpen, setIsIdentityDialogOpen] = useState(false);
  const [emailForm, setEmailForm] = useState({
    newEmail: '',
    currentPassword: '',
  });
  const [emailLoading, setEmailLoading] = useState(false);


  // 2FA State
  const [is2FADialogOpen, setIs2FADialogOpen] = useState(false);
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
      setIsPasswordPasswordDialogOpen(false);
      fetchAuditLogs();
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
      setIsIdentityDialogOpen(false);
      fetchAuditLogs();
    } catch (error: any) {
      setToast({ message: error.message, type: 'error' });
    } finally {
      setEmailLoading(false);
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
          console.error(t('failedToStart2FASetup'), error);
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
              await update({ user: { is_two_fa_enabled: true } });
              setToast({ message: t('twoFAEnabled'), type: 'success' });
              setShow2FASetup(false);
              setTwoFACode('');
              setIs2FADialogOpen(false);
              fetchAuditLogs();
          } else {
              const data = await res.json();
              throw new Error(data.detail || t('verificationFailed'));
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      } finally {
          setTwoFALoading(false);
      }
  };

  const handleDisable2FA = async () => {
      if (!confirm(t('confirmDisable2FA'))) return;
      try {
          const res = await authenticatedFetch('/api/v1/auth/2fa', sessionData, { method: 'DELETE' });
          if (res.ok) {
              await update({ user: { is_two_fa_enabled: false } });
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
              throw new Error(t('failedToRevokeSession'));
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
          {t('securitySubtitle')}
        </p>
      </div>

      {/* Security Overview Control Card */}
      <Card className="p-6">
          <div className="flex flex-col gap-6">
              <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
                      <Shield className="w-6 h-6" />
                  </div>
                  <div>
                      <h3 className="text-base font-bold">{t('securityOperations')}</h3>
                      <p className="text-xs text-slate-500">{t('securityOpsDesc')}</p>
                  </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Password Control */}
                  <Dialog open={isPasswordDialogOpen} onOpenChange={setIsPasswordPasswordDialogOpen}>
                      <DialogTrigger asChild>
                          <button className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl hover:border-blue-500/50 transition-all group">
                              <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-lg bg-white dark:bg-slate-800 flex items-center justify-center text-slate-500 group-hover:text-blue-500 transition-colors">
                                      <Lock className="w-4 h-4" />
                                  </div>
                                  <span className="text-sm font-bold">{t('changePassword')}</span>
                              </div>
                              <ChevronRight className="w-4 h-4 text-slate-300" />
                          </button>
                      </DialogTrigger>
                      <DialogContent>
                          <DialogHeader>
                              <DialogTitle>{t('changePassword')}</DialogTitle>
                              <DialogDescription>{t('passwordModalDesc')}</DialogDescription>
                          </DialogHeader>
                          <form onSubmit={handlePasswordChange} className="flex flex-col gap-4 py-4">
                              <div className="flex flex-col gap-1.5">
                                  <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('currentPassword')}</label>
                                  <input
                                      type="password" required
                                      value={passwordForm.currentPassword}
                                      onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                                  />
                              </div>
                              <div className="flex flex-col gap-1.5">
                                  <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('newPassword')}</label>
                                  <input
                                      type="password" required
                                      value={passwordForm.newPassword}
                                      onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                                  />
                              </div>
                              <div className="flex flex-col gap-1.5">
                                  <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('confirmNewPassword')}</label>
                                  <input
                                      type="password" required
                                      value={passwordForm.confirmPassword}
                                      onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                                  />
                              </div>
                              <DialogFooter className="mt-4">
                                  <button
                                      type="submit"
                                      disabled={passwordLoading}
                                      className="w-full sm:w-auto px-8 py-2.5 bg-blue-600 text-white text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                                  >
                                      {passwordLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                      {t('saveChanges')}
                                  </button>
                              </DialogFooter>
                          </form>
                      </DialogContent>
                  </Dialog>

                  {/* Identity Info Control (Email/Phone) */}
                  <Dialog open={isIdentityDialogOpen} onOpenChange={setIsIdentityDialogOpen}>
                      <DialogTrigger asChild>
                          <button className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl hover:border-emerald-500/50 transition-all group">
                              <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-lg bg-white dark:bg-slate-800 flex items-center justify-center text-slate-500 group-hover:text-emerald-500 transition-colors">
                                      <Fingerprint className="w-4 h-4" />
                                  </div>
                                  <span className="text-sm font-bold">{t('verificationInfo')}</span>
                              </div>
                              <ChevronRight className="w-4 h-4 text-slate-300" />
                          </button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                          <DialogHeader>
                              <DialogTitle>{t('verificationDetails')}</DialogTitle>
                              <DialogDescription>{t('verificationDesc')}</DialogDescription>
                          </DialogHeader>
                          
                          <div className="grid grid-cols-1 gap-8 py-4">
                              {/* Email Sub-section */}
                              <div className="flex flex-col gap-4">
                                  <h4 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                                      <MailCheck className="w-3.5 h-3.5" /> {t('changeEmail')}
                                  </h4>
                                  <form onSubmit={handleEmailChangeRequest} className="flex flex-col gap-3">
                                      <div className="flex flex-col gap-1.5">
                                          <label className="text-[10px] font-bold text-slate-500">{t('newEmail')}</label>
                                          <input
                                              type="email" required
                                              value={emailForm.newEmail}
                                              onChange={(e) => setEmailForm({ ...emailForm, newEmail: e.target.value })}
                                              className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                                          />
                                      </div>
                                      <div className="flex flex-col gap-1.5">
                                          <label className="text-[10px] font-bold text-slate-500">{t('confirmWithPassword')}</label>
                                          <input
                                              type="password" required
                                              value={emailForm.currentPassword}
                                              onChange={(e) => setEmailForm({ ...emailForm, currentPassword: e.target.value })}
                                              className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                                          />
                                      </div>
                                      <button
                                          type="submit" disabled={emailLoading}
                                          className="w-full py-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                                      >
                                          {emailLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                          {t('initiateChange')}
                                      </button>
                                  </form>
                              </div>

                          </div>
                      </DialogContent>
                  </Dialog>

                  {/* 2FA Control */}
                  <Dialog open={is2FADialogOpen} onOpenChange={setIs2FADialogOpen}>
                      <DialogTrigger asChild>
                          <button className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl hover:border-amber-500/50 transition-all group text-left">
                              <div className="flex items-center gap-3">
                                  <div className={`w-8 h-8 rounded-lg bg-white dark:bg-slate-800 flex items-center justify-center transition-colors ${sessionData?.user?.is_two_fa_enabled ? 'text-emerald-500' : 'text-slate-500 group-hover:text-amber-500'}`}>
                                      {sessionData?.user?.is_two_fa_enabled ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
                                  </div>
                                  <div className="flex flex-col">
                                      <span className="text-sm font-bold">{t('twoFA')}</span>
                                      <span className={`text-[9px] font-black uppercase ${sessionData?.user?.is_two_fa_enabled ? 'text-emerald-500' : 'text-slate-400'}`}>
                                          {sessionData?.user?.is_two_fa_enabled ? t('enabled') : t('disabled')}
                                      </span>
                                  </div>
                              </div>
                              <ChevronRight className="w-4 h-4 text-slate-300" />
                          </button>
                      </DialogTrigger>
                      <DialogContent>
                          <DialogHeader>
                              <DialogTitle>{t('twoFA')}</DialogTitle>
                              <DialogDescription>{t('twoFAModalDesc')}</DialogDescription>
                          </DialogHeader>
                          
                          <div className="py-4">
                              {sessionData?.user?.is_two_fa_enabled ? (
                                  <div className="flex flex-col gap-6 items-center text-center">
                                      <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600">
                                          <ShieldCheck className="w-8 h-8" />
                                      </div>
                                      <div className="flex flex-col gap-1">
                                          <h4 className="font-bold">{t('twoFAEnabled')}</h4>
                                          <p className="text-xs text-slate-500">{t('twoFAEnabledMsg')}</p>
                                      </div>
                                      <button 
                                          onClick={handleDisable2FA}
                                          className="w-full py-2.5 bg-red-50 text-red-600 text-xs font-bold rounded-lg hover:bg-red-100 transition-colors"
                                      >
                                          {t('disable2FA')}
                                      </button>
                                  </div>
                              ) : (
                                  <div className="flex flex-col gap-4">
                                      {!show2FASetup ? (
                                          <div className="flex flex-col gap-6 items-center text-center">
                                              <div className="w-16 h-16 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center text-amber-600">
                                                  <KeyRound className="w-8 h-8" />
                                              </div>
                                              <p className="text-xs text-slate-500 leading-relaxed max-w-xs">
                                                  {t('twoFAActionRequiredMsg')}
                                              </p>
                                              <button 
                                                  onClick={handleStart2FASetup}
                                                  className="w-full py-2.5 bg-blue-600 text-white text-xs font-bold rounded-lg shadow-lg shadow-blue-500/20"
                                              >
                                                  {t('setup2FA')}
                                              </button>
                                          </div>
                                      ) : (
                                          <form onSubmit={handleVerify2FA} className="flex flex-col gap-6">
                                              <div className="flex flex-col items-center gap-4">
                                                  <div className="bg-white p-2 rounded-xl shadow-xl border border-slate-100">
                                                      <img src={qrCodeUrl!} alt="2FA QR Code" className="w-40 h-40" />
                                                  </div>
                                                  <p className="text-xs text-center text-slate-500 px-4">
                                                      {t('scanQRCode')}
                                                  </p>
                                                  <div className="w-full h-px bg-slate-100 dark:bg-slate-800"></div>
                                                  <div className="flex flex-col gap-2 w-full">
                                                      <label className="text-[10px] font-bold uppercase text-slate-500 text-center">{t('enterCodeFromApp')}</label>
                                                      <input
                                                          type="text" required maxLength={6} placeholder="000000"
                                                          value={twoFACode}
                                                          onChange={(e) => setTwoFACode(e.target.value)}
                                                          className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-3 text-lg text-center font-mono tracking-[0.5em] focus:outline-none focus:border-blue-500"
                                                      />
                                                  </div>
                                              </div>
                                              <div className="flex gap-2">
                                                  <button
                                                      type="submit" disabled={twoFALoading || twoFACode.length !== 6}
                                                      className="flex-1 py-2.5 bg-blue-600 text-white text-xs font-bold rounded-lg disabled:opacity-50"
                                                  >
                                                      {twoFALoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                                      {t('enable2FA')}
                                                  </button>
                                                  <button 
                                                      type="button" onClick={() => setShow2FASetup(false)}
                                                      className="px-4 py-2.5 bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs font-bold rounded-lg"
                                                  >
                                                      {t('close')}
                                                  </button>
                                              </div>
                                          </form>
                                      )}
                                  </div>
                              )}
                          </div>
                      </DialogContent>
                  </Dialog>
              </div>
          </div>
      </Card>

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
                            <th className="px-6 py-4 text-right">{t('action')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {sessionsLoading ? (
                            <tr>
                                <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                                    {t('loadingSessions')}
                                </td>
                            </tr>
                        ) : sessions.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                                    {t('noSessions')}
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
                                                    {sess.device_info?.name || t('unknownDevice')}
                                                </div>
                                                <div className="text-xs text-slate-500">
                                                    {sess.is_current ? t('currentSession') : t('otherSession')}
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
                                                {t('unknownLocation')}
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
                                      {t('loadingLogs')}
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