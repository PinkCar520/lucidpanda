'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Key, Plus, Trash2, Copy, Shield, AlertCircle, Loader2, CheckCircle2, Globe, Clock } from 'lucide-react';
import Toast from '@/components/Toast';
import { authenticatedFetch } from '@/lib/api-client';

interface APIKey {
    id: string;
    name: string;
    public_key: string;
    permissions: string[];
    ip_whitelist: string[] | null;
    is_active: boolean;
    created_at: string;
    last_used_at: string | null;
    expires_at: string | null;
}

export default function APIKeysPage() {
  const t = useTranslations('Settings');
  const { data: sessionData } = useSession();
  
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyData, setNewKeyData] = useState<{ public_key: string; secret: string } | null>(null);
  
  const [formData, setFormData] = useState({
      name: '',
      permissions: ['read_only'],
      ip_whitelist: '',
      expires_at: ''
  });

  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (sessionData) {
        fetchKeys();
    }
  }, [sessionData]);

  const fetchKeys = async () => {
    try {
        const res = await authenticatedFetch('/api/v1/auth/api-keys/me', sessionData);
        if (res.ok) {
            const data = await res.json();
            setKeys(data);
        }
    } catch (error) {
        console.error("Failed to fetch API keys", error);
    } finally {
        setLoading(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
      e.preventDefault();
      setCreating(true);
      try {
          const res = await authenticatedFetch('/api/v1/auth/api-keys/me', sessionData, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  ...formData,
                  ip_whitelist: formData.ip_whitelist ? formData.ip_whitelist.split(',').map(s => s.trim()) : null,
                  expires_at: formData.expires_at || null
              })
          });
          if (res.ok) {
              const data = await res.json();
              setNewKeyData({ public_key: data.public_key, secret: data.secret });
              fetchKeys();
              setToast({ message: t('apiKeyCreated'), type: 'success' });
              setFormData({ name: '', permissions: ['read_only'], ip_whitelist: '', expires_at: '' });
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      } finally {
          setCreating(false);
      }
  };

  const handleRevokeKey = async (keyId: string) => {
      if (!confirm(t('confirmRevokeKey'))) return;
      try {
          const res = await authenticatedFetch(`/api/v1/auth/api-keys/me/${keyId}`, sessionData, {
              method: 'DELETE'
          });
          if (res.ok) {
              setKeys(keys.filter(k => k.id !== keyId));
              setToast({ message: t('apiKeyRevoked'), type: 'success' });
          }
      } catch (error: any) {
          setToast({ message: error.message, type: 'error' });
      }
  };

  const copyToClipboard = (text: string) => {
      navigator.clipboard.writeText(text);
      setToast({ message: t('copiedToClipboard'), type: 'success' });
  };

  if (loading) {
      return (
          <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
      );
  }

  return (
    <div className="flex flex-col gap-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold">{t('apiKeys')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t('manageAPIKeys')}
        </p>
      </div>

      {newKeyData && (
          <Card className="p-6 border-amber-500/50 bg-amber-500/5 animate-in zoom-in-95">
              <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-bold text-sm">
                      <AlertCircle className="w-4 h-4" />
                      {t('secretWarning')}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('publicKey')}</label>
                          <div className="flex gap-2">
                              <input readOnly value={newKeyData.public_key} className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded px-3 py-2 text-xs font-mono" />
                              <button onClick={() => copyToClipboard(newKeyData.public_key)} className="p-2 bg-slate-100 dark:bg-slate-800 rounded"><Copy className="w-4 h-4" /></button>
                          </div>
                      </div>
                      <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('secretKey')}</label>
                          <div className="flex gap-2">
                              <input readOnly value={newKeyData.secret} className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded px-3 py-2 text-xs font-mono" />
                              <button onClick={() => copyToClipboard(newKeyData.secret)} className="p-2 bg-slate-100 dark:bg-slate-800 rounded text-amber-600"><Copy className="w-4 h-4" /></button>
                          </div>
                      </div>
                  </div>
                  <button 
                    onClick={() => setNewKeyData(null)}
                    className="mt-2 text-xs font-bold text-slate-500 hover:text-slate-700"
                  >
                      {t('savedSecretKey')}
                  </button>
              </div>
          </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Create Key Form */}
          <div className="lg:col-span-1">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
                  <Plus className="w-4 h-4 text-blue-500" />
                  {t('createAPIKey')}
              </div>
              <Card className="p-6">
                  <form onSubmit={handleCreateKey} className="flex flex-col gap-4">
                      <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('keyName')}</label>
                          <input 
                            required
                            placeholder="e.g. Trading Bot"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                          />
                      </div>
                      <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('ipWhitelist')} (Optional)</label>
                          <input 
                            placeholder="1.2.3.4, 5.6.7.8"
                            value={formData.ip_whitelist}
                            onChange={(e) => setFormData({ ...formData, ip_whitelist: e.target.value })}
                            className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                          />
                      </div>
                      <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('expiresAt')} (Optional)</label>
                          <input 
                            type="date"
                            value={formData.expires_at}
                            onChange={(e) => setFormData({ ...formData, expires_at: e.target.value })}
                            className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                          />
                      </div>
                      <button 
                        type="submit"
                        disabled={creating}
                        className="mt-2 w-full py-2 bg-blue-600 dark:bg-emerald-500 text-white text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20"
                      >
                          {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                          {t('createAPIKey')}
                      </button>
                  </form>
              </Card>
          </div>

          {/* Keys List */}
          <div className="lg:col-span-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
                  <Key className="w-4 h-4 text-indigo-500" />
                  {t('yourAPIKeys')}
              </div>
              <div className="flex flex-col gap-4">
                  {keys.length === 0 ? (
                      <Card className="p-12 text-center text-slate-500 flex flex-col items-center gap-2">
                          <Key className="w-8 h-8 opacity-20" />
                          <p className="text-sm">{t('noAPIKeys')}</p>
                      </Card>
                  ) : (
                      keys.map((key) => (
                          <Card key={key.id} className="p-6">
                              <div className="flex flex-col md:flex-row gap-6">
                                  <div className="flex-1">
                                      <div className="flex items-center gap-3 mb-2">
                                          <h3 className="font-bold text-slate-900 dark:text-white">{key.name}</h3>
                                          <span className={`text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded ${key.is_active ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                                              {key.is_active ? t('active') : t('revoked')}
                                          </span>
                                      </div>
                                      <div className="flex flex-col gap-2">
                                          <div className="flex items-center gap-2 text-xs font-mono text-slate-500 bg-slate-50 dark:bg-slate-900/50 p-2 rounded border border-slate-100 dark:border-slate-800 w-fit">
                                              <span>{key.public_key}</span>
                                              <button onClick={() => copyToClipboard(key.public_key)} className="hover:text-slate-900 dark:hover:text-white"><Copy className="w-3 h-3" /></button>
                                          </div>
                                          <div className="flex flex-wrap gap-4 mt-2">
                                              <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                                                  <Clock className="w-3.5 h-3.5" />
                                                  {t('lastUsed')}: {key.last_used_at ? new Date(key.last_used_at).toLocaleString() : t('neverUsed')}
                                              </div>
                                              <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                                                  <Shield className="w-3.5 h-3.5" />
                                                  {key.permissions.join(', ')}
                                              </div>
                                              {key.ip_whitelist && (
                                                  <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                                                      <Globe className="w-3.5 h-3.5" />
                                                      {key.ip_whitelist.length} IPs
                                                  </div>
                                              )}
                                          </div>
                                      </div>
                                  </div>
                                  <div className="shrink-0 flex md:flex-col justify-end gap-2">
                                      <button 
                                        onClick={() => handleRevokeKey(key.id)}
                                        className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors border border-transparent hover:border-red-200 dark:hover:border-red-900/50 flex items-center gap-2 text-xs font-bold"
                                      >
                                          <Trash2 className="w-4 h-4" />
                                          {t('revokeKey')}
                                      </button>
                                  </div>
                              </div>
                          </Card>
                      ))
                  )}
              </div>
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
