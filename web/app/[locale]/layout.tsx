import type { Metadata } from "next";
// import { Inter } from "next/font/google";
import "../globals.css";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { SessionProvider } from 'next-auth/react'; // Import SessionProvider

export const metadata: Metadata = {
    title: "AlphaSignal Dashboard",
    description: "AI-Driven Geopolitical Intelligence Terminal",
};

export default async function LocaleLayout({
    children,
    params
}: Readonly<{
    children: React.ReactNode;
    params: Promise<{ locale: string }>;
}>) {
    // Next.js 15: params is a Promise
    const { locale } = await params;

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
