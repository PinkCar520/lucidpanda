'use client';

import React, { useEffect, useRef, memo } from 'react';

function TradingViewMiniCharts() {
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

        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/external-embedding/embed-widget-tickers.js";
        script.type = "text/javascript";
        script.async = true;
        script.innerHTML = JSON.stringify({
            "symbols": [
                {
                    "description": "Gold",
                    "proName": "OANDA:XAUUSD"
                },
                {
                    "description": "DXY",
                    "proName": "CAPITALCOM:DXY"
                },
                {
                    "description": "US10Y (Pyth)",
                    "proName": "PYTH:US10Y"
                },
                {
                    "description": "Oil",
                    "proName": "TVC:USOIL"
                },
                {
                    "description": "VIX",
                    "proName": "CAPITALCOM:VIX"
                }
            ],
            "colorTheme": theme,
            "isTransparent": true,
            "showSymbolLogo": true,
            "locale": "en"
        });

        const widgetContainer = document.createElement('div');
        widgetContainer.className = "tradingview-widget-container__widget";
        container.current.appendChild(widgetContainer);
        container.current.appendChild(script);

    }, [theme]);

    return (
        <div className="tradingview-widget-container w-full" ref={container}>
            {/* Widget will be injected here */}
        </div>
    );
}

export default memo(TradingViewMiniCharts);
