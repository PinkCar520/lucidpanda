'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Bell, Mail, Smartphone, Zap, Loader2, Save, Inbox, CheckCheck } from 'lucide-react';
import Toast from '@/components/Toast';
import { authenticatedFetch } from '@/lib/api-client';

interface Message {
    id: string;
    subject: string;
    content: string;
    sender_type: string;
    is_read: boolean;
    sent_at: string;
}

export default function NotificationsPage() {
  const t = useTranslations('Settings');
  const { data: sessionData } = useSession();
  
  const [prefs, setPrefs] = useState({
    email_enabled: true,
    sms_enabled: false,
    app_push_enabled: false,
    email_frequency: 'daily',
    sms_frequency: 'immediate',
    subscribed_types: [] as string[]
  });
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (sessionData) {
        Promise.all([fetchPrefs(), fetchMessages()]).finally(() => setLoading(false));
    }
  }, [sessionData]);

  const fetchPrefs = async () => {
    try {
        const res = await authenticatedFetch('/api/v1/auth/notifications/me/preferences', sessionData);
        if (res.ok) {
            const data = await res.json();
            setPrefs(data);
        }
    } catch (error) {
        console.error("Failed to fetch notification preferences", error);
    }
  };

  const fetchMessages = async () => {
      try {
          const res = await authenticatedFetch('/api/v1/auth/notifications/me/inbox', sessionData);
          if (res.ok) {
              const data = await res.json();
              setMessages(data);
          }
      } catch (error) {
          console.error("Failed to fetch inbox", error);
      }
  };

  const handleMarkRead = async (msgId: string) => {
      try {
          const res = await authenticatedFetch(`/api/v1/auth/notifications/me/inbox/${msgId}/read`, sessionData, { method: 'PUT' });
          if (res.ok) {
              setMessages(messages.map(m => m.id === msgId ? { ...m, is_read: true } : m));
          }
      } catch (error) {
          console.error("Failed to mark message read", error);
      }
  };

  const handleToggle = (key: string) => {
      setPrefs(prev => ({ ...prev, [key]: !(prev as any)[key] }));
  };

  const handleFrequencyChange = (key: string, value: string) => {
      setPrefs(prev => ({ ...prev, [key]: value }));
  };

  const handleTypeToggle = (type: string) => {
      setPrefs(prev => {
          const types = [...prev.subscribed_types];
          if (types.includes(type)) {
              return { ...prev, subscribed_types: types.filter(t => t !== type) };
          } else {
              return { ...prev, subscribed_types: [...types, type] };
          }
      });
  };

  const handleSaveChanges = async () => {
      setSaving(true);
      try {
          const res = await authenticatedFetch('/api/v1/auth/notifications/me/preferences', sessionData, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(prefs)
          });
          if (res.ok) {
              setToast({ message: t('saveChanges'), type: 'success' });
          } else {
              throw new Error('Failed to save preferences');
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      } finally {
          setSaving(false);
      }
  };

  if (loading) {
      return (
          <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
      );
  }

  const subscriptionTypes = [
      { id: 'trading_alerts', label: t('tradingAlerts') },
      { id: 'system_announcements', label: t('systemAnnouncements') },
      { id: 'security_alerts', label: t('securityAlerts') },
      { id: 'market_news', label: t('marketNews') }
  ];

  return (
    <div className="flex flex-col gap-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold">{t('notifications')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Control how and when you receive updates from AlphaSignal.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8">
        {/* Channels */}
        <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                <Zap className="w-4 h-4 text-amber-500" />
                {t('notificationChannels')}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Email */}
                <Card className={`p-6 border-2 transition-all ${prefs.email_enabled ? 'border-blue-500/50 bg-blue-500/5' : 'border-slate-200 dark:border-slate-800'}`}>
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600">
                                <Mail className="w-5 h-5" />
                            </div>
                            <button 
                                onClick={() => handleToggle('email_enabled')}
                                className={`w-10 h-5 rounded-full transition-colors relative ${prefs.email_enabled ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}
                            >
                                <div className={`absolute top-1 left-1 w-3 h-3 rounded-full bg-white transition-transform ${prefs.email_enabled ? 'translate-x-5' : ''}`} />
                            </button>
                        </div>
                        <div>
                            <h3 className="text-sm font-bold">{t('emailNotifications')}</h3>
                            <p className="text-[10px] text-slate-500 mt-1">Receive updates via your verified email address.</p>
                        </div>
                        <div className="flex flex-col gap-1.5 mt-2">
                            <label className="text-[9px] font-bold uppercase tracking-widest text-slate-400">{t('frequency')}</label>
                            <select 
                                value={prefs.email_frequency}
                                onChange={(e) => handleFrequencyChange('email_frequency', e.target.value)}
                                disabled={!prefs.email_enabled}
                                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded px-2 py-1 text-xs focus:outline-none disabled:opacity-50"
                            >
                                <option value="immediate">{t('immediate')}</option>
                                <option value="daily">{t('daily')}</option>
                                <option value="weekly">{t('weekly')}</option>
                            </select>
                        </div>
                    </div>
                </Card>

                {/* SMS */}
                <Card className={`p-6 border-2 transition-all ${prefs.sms_enabled ? 'border-purple-500/50 bg-purple-500/5' : 'border-slate-200 dark:border-slate-800'}`}>
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600">
                                <Smartphone className="w-5 h-5" />
                            </div>
                            <button 
                                onClick={() => handleToggle('sms_enabled')}
                                className={`w-10 h-5 rounded-full transition-colors relative ${prefs.sms_enabled ? 'bg-purple-600' : 'bg-slate-300 dark:bg-slate-700'}`}
                            >
                                <div className={`absolute top-1 left-1 w-3 h-3 rounded-full bg-white transition-transform ${prefs.sms_enabled ? 'translate-x-5' : ''}`} />
                            </button>
                        </div>
                        <div>
                            <h3 className="text-sm font-bold">{t('smsNotifications')}</h3>
                            <p className="text-[10px] text-slate-500 mt-1">Direct alerts to your bound phone number.</p>
                        </div>
                        <div className="flex flex-col gap-1.5 mt-2">
                            <label className="text-[9px] font-bold uppercase tracking-widest text-slate-400">{t('frequency')}</label>
                            <select 
                                value={prefs.sms_frequency}
                                onChange={(e) => handleFrequencyChange('sms_frequency', e.target.value)}
                                disabled={!prefs.sms_enabled}
                                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded px-2 py-1 text-xs focus:outline-none disabled:opacity-50"
                            >
                                <option value="immediate">{t('immediate')}</option>
                                <option value="daily">{t('daily')}</option>
                            </select>
                        </div>
                    </div>
                </Card>

                {/* App Push */}
                <Card className={`p-6 border-2 transition-all ${prefs.app_push_enabled ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-slate-200 dark:border-slate-800'}`}>
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <div className="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600">
                                <Bell className="w-5 h-5" />
                            </div>
                            <button 
                                onClick={() => handleToggle('app_push_enabled')}
                                className={`w-10 h-5 rounded-full transition-colors relative ${prefs.app_push_enabled ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-700'}`}
                            >
                                <div className={`absolute top-1 left-1 w-3 h-3 rounded-full bg-white transition-transform ${prefs.app_push_enabled ? 'translate-x-5' : ''}`} />
                            </button>
                        </div>
                        <div>
                            <h3 className="text-sm font-bold">{t('pushNotifications')}</h3>
                            <p className="text-[10px] text-slate-500 mt-1">Browser and mobile push notifications.</p>
                        </div>
                        <div className="mt-auto pt-4">
                            <div className="text-[10px] text-slate-400 italic">Push enabled for 2 devices.</div>
                        </div>
                    </div>
                </Card>
            </div>
        </div>

        {/* Subscription Types */}
        <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                <Zap className="w-4 h-4 text-blue-500" />
                {t('subscriptionTypes')}
            </div>
            <Card className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {subscriptionTypes.map((type) => (
                        <div key={type.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                            <div className="flex flex-col">
                                <span className="text-sm font-bold">{type.label}</span>
                                <span className="text-[10px] text-slate-500">Alerts for critical events.</span>
                            </div>
                            <button 
                                onClick={() => handleTypeToggle(type.id)}
                                className={`w-10 h-5 rounded-full transition-colors relative ${prefs.subscribed_types.includes(type.id) ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}
                            >
                                <div className={`absolute top-1 left-1 w-3 h-3 rounded-full bg-white transition-transform ${prefs.subscribed_types.includes(type.id) ? 'translate-x-5' : ''}`} />
                            </button>
                        </div>
                    ))}
                </div>
            </Card>
        </div>

        <div className="flex justify-end pt-4">
            <button 
                onClick={handleSaveChanges}
                disabled={saving}
                className="px-8 py-3 bg-blue-600 dark:bg-emerald-500 text-white text-sm font-bold rounded-xl hover:opacity-90 transition-opacity shadow-lg shadow-blue-500/20 flex items-center gap-2"
            >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {t('saveChanges')}
            </button>
        </div>

        {/* Inbox */}
        <div className="flex flex-col gap-4 mt-8 border-t border-slate-100 dark:border-slate-800 pt-8">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                <Inbox className="w-4 h-4 text-blue-500" />
                {t('inbox')}
            </div>
            <Card className="overflow-hidden">
                <div className="flex flex-col divide-y divide-slate-100 dark:divide-slate-800">
                    {messages.length === 0 ? (
                        <div className="p-12 text-center text-slate-500 flex flex-col items-center gap-2">
                            <Inbox className="w-8 h-8 opacity-20" />
                            <p className="text-sm">{t('noMessages')}</p>
                        </div>
                    ) : (
                        messages.map((msg) => (
                            <div key={msg.id} className={`p-4 hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors flex gap-4 ${!msg.is_read ? 'bg-blue-500/5' : ''}`}>
                                <div className={`w-2 h-2 rounded-full mt-2 shrink-0 ${!msg.is_read ? 'bg-blue-500' : 'bg-transparent'}`} />
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-4">
                                        <h4 className={`text-sm font-bold truncate ${!msg.is_read ? 'text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'}`}>
                                            {msg.subject}
                                        </h4>
                                        <span className="text-[10px] text-slate-400 whitespace-nowrap">{new Date(msg.sent_at).toLocaleString()}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{msg.content}</p>
                                    <div className="flex items-center gap-3 mt-3">
                                        <span className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-slate-500">
                                            {msg.sender_type}
                                        </span>
                                        {!msg.is_read && (
                                            <button 
                                                onClick={() => handleMarkRead(msg.id)}
                                                className="text-[9px] font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
                                            >
                                                <CheckCheck className="w-3 h-3" />
                                                {t('markAsRead')}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </Card>
        </div>
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
