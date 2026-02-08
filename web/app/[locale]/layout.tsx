import type { Metadata } from "next";
// import { Inter } from "next/font/google";
import "../globals.css";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslations } from 'next-intl/server';
import { SessionProvider } from 'next-auth/react'; // Import SessionProvider
import Shell from '@/components/Shell';

export async function generateMetadata({
    params
}: {
    params: Promise<{ locale: string }>;
}): Promise<Metadata> {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'App' });
    return {
        title: t('title'),
        description: t('description'),
    };
}

export default async function LocaleLayout({
    children,
    params
}: Readonly<{
    children: React.ReactNode;
    params: Promise<{ locale: string }>;
}>) {
    const { locale } = await params;

    // Providing all messages to the client
    // side is the easiest way to get started
    const messages = await getMessages();

    return (
        <html lang={locale}>
            <body className="antialiased font-sans">
                <NextIntlClientProvider messages={messages}>
                    <SessionProvider> {/* Wrap children with SessionProvider */}
                        <Shell>
                            {children}
                        </Shell>
                    </SessionProvider>
                </NextIntlClientProvider>
            </body>
        </html>
    );
}
