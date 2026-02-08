'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { useParams } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { User, Mail, Calendar, ShieldCheck, Loader2, Camera, MapPin, Globe } from 'lucide-react';
import Toast from '@/components/Toast';
import { authenticatedFetch } from '@/lib/api-client';
import Image from 'next/image';

export default function ProfilePage() {
  const t = useTranslations('Settings');
  const { data: session, update } = useSession();
  const { locale } = useParams(); // Get locale for date formatting
  
  const [formData, setFormData] = useState({
    name: '',
    nickname: '',
    gender: '',
    birthday: '',
    location: '',
    timezone: '',
    language_preference: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (session?.user?.avatar_url) {
      setImageError(false);
    }
  }, [session?.user?.avatar_url]);

  useEffect(() => {
    if (session?.user) {
      let birthdayStr = '';
      if (session.user.birthday) {
          const date = new Date(session.user.birthday);
          if (!isNaN(date.getTime())) {
              birthdayStr = date.toISOString().split('T')[0];
          }
      }
      setFormData({
        name: session.user.name || '',
        nickname: session.user.nickname || '',
        gender: session.user.gender || '',
        birthday: birthdayStr,
        location: session.user.location || '',
        timezone: session.user.timezone || 'UTC',
        language_preference: session.user.language_preference || 'en'
      });
    }
  }, [session]);


  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await authenticatedFetch('/api/v1/auth/me', session, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            ...formData,
            birthday: formData.birthday || null // Handle empty string for date
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        console.error('[Profile] Update failed:', res.status, errorData);
        throw new Error(errorData.detail || 'Failed to update profile');
      }

      const updatedUser = await res.json();
      console.log('[Profile] Update success:', updatedUser);
      
      // Update NextAuth session
      try {
        await update({
          ...session,
          user: {
            ...session?.user,
            ...updatedUser,
          },
        });
        console.log('[Profile] Session updated');
      } catch (sessErr) {
        console.error('[Profile] Session update failed:', sessErr);
      }

      setToast({ message: t('profileUpdateSuccess'), type: 'success' });
    } catch (error: any) {
      console.error('[Profile] Error:', error);
      setToast({ message: error.message || t('profileUpdateError'), type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingAvatar(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await authenticatedFetch('/api/v1/auth/me/avatar', session, {
        method: 'PUT',
        body: formData,
      });

      if (!res.ok) throw new Error('Failed to upload avatar');

      const data = await res.json();
      console.log('[Avatar] Upload success:', data);
      
      // Update NextAuth session
      try {
        await update({
          ...session,
          user: {
              ...session?.user,
              avatar_url: data.avatar_url
          }
        });
        console.log('[Avatar] Session updated');
      } catch (sessErr) {
        console.error('[Avatar] Session update failed:', sessErr);
      }
      
      setToast({ message: t('avatarUpdateSuccess'), type: 'success' });
    } catch (error: any) {
      console.error('[Avatar] Error:', error);
      setToast({ message: t('avatarUpdateError'), type: 'error' });
    } finally {
      setUploadingAvatar(false);
    }
  };

  if (!session) return null;

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold">{t('basicInfo')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t('profileSubtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Card */}
        <Card className="lg:col-span-1 flex flex-col items-center text-center p-8 h-fit">
          <div className="mb-6 flex flex-col items-center">
            <div className="relative group cursor-pointer" onClick={handleAvatarClick}>
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-600 to-indigo-500 flex items-center justify-center text-white text-3xl font-black shadow-xl shadow-blue-500/20 overflow-hidden relative">
                {session.user?.avatar_url && !imageError ? (
                    <Image 
                      src={session.user.avatar_url} 
                      alt="Avatar" 
                      width={96} 
                      height={96} 
                      className="w-full h-full object-cover"
                      onError={() => setImageError(true)}
                      unoptimized={true}
                    />
                ) : (
                    session.user?.name?.[0]?.toUpperCase() || session.user?.email?.[0]?.toUpperCase()
                )}
                </div>
                
                {/* Hover Overlay */}
                <div className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <Camera className="w-6 h-6 text-white" />
                </div>

                {/* Uploading Spinner Overlay */}
                {uploadingAvatar && (
                    <div className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center">
                        <Loader2 className="w-6 h-6 text-white animate-spin" />
                    </div>
                )}
                
                <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleAvatarChange} 
                    className="hidden" 
                    accept="image/jpeg,image/png,image/webp"
                />
            </div>
          </div>
          
          <h3 className="text-lg font-bold">{session.user?.name || t('anonymousUser')}</h3>
          <p className="text-xs text-slate-500 font-mono mb-4">{session.user?.email}</p>
          <Badge variant="neutral" className="uppercase tracking-widest text-[10px]">
            {session.user?.role || t('defaultRole')}
          </Badge>
          
          <div className="w-full border-t border-slate-100 dark:border-slate-800 mt-6 pt-6 flex flex-col gap-3">
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>{t('identityVerified')}</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <Calendar className="w-4 h-4" />
              <span>{t('memberSince', { date: new Date(session.user?.created_at || Date.now()).toLocaleDateString(locale, { month: 'short', year: 'numeric' })})}</span>
            </div>
            {/* The clickable area for avatar upload is the entire div, no explicit button needed. */}
          </div>
        </Card>

        {/* Edit Form */}
        <Card className="lg:col-span-2 p-6">
          <form onSubmit={handleUpdateProfile} className="flex flex-col gap-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {t('fullName')}
                </label>
                <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder={t('fullNamePlaceholder')}
                    />
                </div>
                </div>

                <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {t('nickname')}
                </label>
                <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                    type="text"
                    name="nickname"
                    value={formData.nickname}
                    onChange={handleInputChange}
                    className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder={t('nicknamePlaceholder')}
                    />
                </div>
                </div>

                <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {t('gender')}
                </label>
                <select
                    name="gender"
                    value={formData.gender}
                    onChange={handleInputChange}
                    className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:border-blue-500 transition-colors appearance-none"
                >
                    <option value="">{t('selectGender')}</option>
                    <option value="male">{t('male')}</option>
                    <option value="female">{t('female')}</option>
                    <option value="other">{t('other')}</option>
                </select>
                </div>

                <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {t('birthday')}
                </label>
                <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                    type="date"
                    name="birthday"
                    value={formData.birthday}
                    onChange={handleInputChange}
                    className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                    />
                </div>
                </div>

                <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {t('location')}
                </label>
                <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleInputChange}
                    className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder={t('locationPlaceholder')}
                    />
                </div>
                </div>

                <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {t('timezone')}
                </label>
                <div className="relative">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <select
                    name="timezone"
                    value={formData.timezone}
                    onChange={handleInputChange}
                    className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors appearance-none"
                    >
                        <option value="UTC">{t('timezoneUTC')}</option>
                        {/* Add more timezones as needed */}
                        <option value="America/New_York">{t('timezoneNewYork')}</option>
                        <option value="Europe/London">{t('timezoneLondon')}</option>
                        <option value="Asia/Shanghai">{t('timezoneShanghai')}</option>
                    </select>
                </div>
                </div>

                <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {t('language')}
                </label>
                <div className="relative">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <select
                    name="language_preference"
                    value={formData.language_preference}
                    onChange={handleInputChange}
                    className="w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:border-blue-500 transition-colors appearance-none"
                    >
                        <option value="en">{t('languageEnglish')}</option>
                        <option value="zh">{t('languageChinese')}</option>
                    </select>
                </div>
                </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {t('emailAddress')}
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
                {t('emailChangeHint')}
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