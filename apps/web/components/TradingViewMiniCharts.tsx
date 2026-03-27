'use client';

import React, { useEffect, useRef, memo } from 'react';

interface TradingViewMiniChartsProps {
    locale: string;
    t: (key: string) => string;
}

function TradingViewMiniCharts({ locale, t }: TradingViewMiniChartsProps) {
    const container = useRef<HTMLDivElement>(null);

    const [theme, setTheme] = React.useState<'light' | 'dark'>('dark');

    useEffect(() => {
        // Initial Theme Check
        const isDark = document.documentElement.classList.contains('dark');
        setTheme(isDark ? 'dark' : 'light');

        // Observer for Theme Changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    const newIsDark = document.documentElement.classList.contains('dark');
                    setTheme(newIsDark ? 'dark' : 'light');
                }
            });
        });

        observer.observe(document.documentElement, { attributes: true });

        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        if (!container.current) return;

        // Clear previous widget content
        container.current.innerHTML = '';

        const widgetContainer = document.createElement('div');
        widgetContainer.className = "tradingview-widget-container__widget";
        
        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/external-embedding/embed-widget-tickers.js";
        script.type = "text/javascript";
        script.async = true;
        script.innerHTML = JSON.stringify({
            "symbols": [
                {
                    "description": t('gold'),
                    "proName": "OANDA:XAUUSD"
                },
                {
                    "description": t('dxy'),
                    "proName": "CAPITALCOM:DXY"
                },
                {
                    "description": t('us10y'),
                    "proName": "PYTH:US10Y"
                },
                {
                    "description": t('oil'),
                    "proName": "TVC:USOIL"
                },
                {
                    "description": t('vix'),
                    "proName": "CAPITALCOM:VIX"
                }
            ],
            "colorTheme": theme,
            "isTransparent": true,
            "showSymbolLogo": true,
            "locale": locale === 'zh' ? 'zh_CN' : locale
        });

        container.current.appendChild(widgetContainer);
        container.current.appendChild(script);

    }, [theme, locale]); // Add locale to dependencies

    return (
        <div className="tradingview-widget-container w-full h-full" ref={container}>
            <div className="tradingview-widget-container__widget h-full"></div>
        </div>
    );
}

export default memo(TradingViewMiniCharts);
