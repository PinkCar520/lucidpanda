'use client';

import React, { useEffect, useRef, memo } from 'react';

interface TradingViewTickerTapeProps {
    locale: string;
    t: (key: string) => string;
}

function TradingViewTickerTape({ locale, t }: TradingViewTickerTapeProps) {
    const container = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!container.current) return;

        // Clear previous widget content to prevent duplicates on re-renders
        container.current.innerHTML = '';

        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
        script.type = "text/javascript";
        script.async = true;
        script.innerHTML = JSON.stringify({
            "symbols": [
                {
                    "description": t('goldSpot'),
                    "proName": "OANDA:XAUUSD"
                },
                {
                    "description": t('dxyIndex'),
                    "proName": "TVC:DXY"
                },
                {
                    "description": t('us10yYield'),
                    "proName": "TVC:US10Y"
                },
                {
                    "description": t('crudeOilWti'),
                    "proName": "TVC:USOIL"
                },
                {
                    "description": t('vixIndex'),
                    "proName": "TVC:VIX"
                },
                {
                    "description": t('sp500'),
                    "proName": "OANDA:SPX500USD"
                }
            ],
            "showSymbolLogo": true,
            "isTransparent": true,
            "displayMode": "adaptive",
            "colorTheme": "dark",
            "locale": locale === 'zh' ? 'zh_CN' : locale
        });

        // Append the standard TradingView wrapper
        const widgetContainer = document.createElement('div');
        widgetContainer.className = "tradingview-widget-container__widget";
        
        container.current.appendChild(widgetContainer);
        container.current.appendChild(script);

    }, [locale]); // Add locale to dependencies

    return (
        <div className="tradingview-widget-container w-full h-12 border-b border-slate-800/50 bg-slate-900/30 backdrop-blur-sm" ref={container}>
            <div className="tradingview-widget-container__widget"></div>
        </div>
    );
}

// Memoize to prevent unnecessary re-renders
export default memo(TradingViewTickerTape);
