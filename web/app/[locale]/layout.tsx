import type { Metadata } from "next";
// import { Inter } from "next/font/google";
import "../globals.css";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslator } from 'next-intl/server';
import { SessionProvider } from 'next-auth/react'; // Import SessionProvider

export async function generateMetadata({
    params: { locale }
}: {
    params: { locale: string };
}): Promise<Metadata> {
    const t = await getTranslator(locale, 'App');
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
    params: { locale: string };
}>) {
    const { locale } = params;

    // Providing all messages to the client
    // side is the easiest way to get started
    const messages = await getMessages();

    return (
        <html lang={locale}>
            <body className="antialiased">
                <NextIntlClientProvider messages={messages}>
                    <SessionProvider> {/* Wrap children with SessionProvider */}
                        {children}
                    </SessionProvider>
                </NextIntlClientProvider>
            </body>
        </html>
    );
}
