import React, { memo } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Zap, ExternalLink } from 'lucide-react';
import { Intelligence } from '@/lib/db';
import { useTranslations } from 'next-intl';
import { useHighlight } from '@/hooks/useHighlight';

interface IntelligenceCardProps {
    item: Intelligence;
    style?: React.CSSProperties;
    locale: string;
    getLocalizedText: (jsonString: string, locale: string) => string;
    t: (key: string) => string;
    tSentiment: (key: string) => string;
    isBearish: boolean;
}

const IntelligenceCard = memo(function IntelligenceCard({
    item,
    style,
    locale,
    getLocalizedText,
    t,
    tSentiment,
    isBearish
}: IntelligenceCardProps) {
    const td = useTranslations('DimensionD');
    const badgeVariant = isBearish ? 'bearish' : 'bullish';
    
    // Trigger highlight when content or summary changes
    const highlightClass = useHighlight(item.id); 

    // Time Decay Logic (Quant Standard)
    const timeDiff = Date.now() - new Date(item.timestamp).getTime();
    const hoursOld = timeDiff / (1000 * 60 * 60);

    let decayClass = 'opacity-100';
    if (hoursOld > 12) {
        decayClass = 'opacity-50 grayscale-[0.5]'; // Old news: dim & desaturate
    } else if (hoursOld > 4) {
        decayClass = 'opacity-75'; // Mid-term: slightly dim
    }

    // We wrap the Card in a div with the style for virtualization positioning
    // or pass style to Card if Card accepts it. Better to wrap to be safe.
    // Note: fixed size list items are absolutely positioned, so 'style' is crucial.
    // We need to ensure we account for spacing (gap). 
    // Usually react-window manages height/top. We can use a margin inside the item to simulate gap.

    return (
        <div style={style} className={`transition-opacity duration-500 ${decayClass}`}>
            <Card
                className={`flex-shrink-0 group hover:bg-white dark:hover:bg-slate-800/40 transition-all duration-200 border border-slate-100 dark:border-slate-800 hover:border-[#165dfc] dark:hover:border-[#165dfc] hover:shadow-md dark:hover:shadow-none h-[calc(100%-12px)] mb-3 overflow-hidden relative ${highlightClass}`}
            >
                <div className="flex justify-between items-start mb-2">
                    <div className="flex gap-2">
                        <Badge variant={item.urgency_score >= 8 ? 'bearish' : 'neutral'}>
                            {tSentiment('score')}: {item.urgency_score}
                        </Badge>
                        <Badge variant={badgeVariant}>
                            {getLocalizedText(item.sentiment, locale)}
                        </Badge>
                    </div>
                    <span className="text-slate-400 dark:text-slate-600 text-[10px] font-data">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })} (UTC)
                    </span>
                </div>

                <h3 className="text-sm font-medium text-slate-800 dark:text-slate-200 mb-2 leading-relaxed group-hover:text-blue-600 dark:group-hover:text-white transition-colors line-clamp-2">
                    {getLocalizedText(item.summary, locale)}
                </h3>

                <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/50">
                    <div className="flex items-center gap-2">
                        <Zap className="w-3 h-3 text-yellow-500" />
                        <span className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[150px]">{item.author}</span>
                    </div>
                    <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 dark:text-emerald-500 text-xs flex items-center gap-1 hover:text-blue-800 dark:hover:text-emerald-300 transition-colors"
                    >
                        {t('viewSource')} <ExternalLink className="w-3 h-3" />
                    </a>
                </div>
            </Card>
        </div>
    );
});

export default IntelligenceCard;
