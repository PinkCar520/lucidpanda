import React, { useState, useMemo, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';
import { X, TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false }) as any;

interface SubSectorStat {
  impact: number;
  weight: number;
}

interface SectorStat {
  impact: number;
  weight: number;
  sub: Record<string, SubSectorStat>;
}

interface Props {
  data: Record<string, SectorStat>;
}

export function SectorAttribution({ data }: Props) {
  const t = useTranslations('Funds');
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);

  if (!data || Object.keys(data).length === 0) return null;

  // Prepare Data for Plotly Treemap
  useEffect(() => {
    const ids: string[] = [];
    const labels: string[] = [];
    const parents: string[] = [];
    const values: number[] = []; // Weight
    const colors: number[] = []; // Impact (for coloring)
    const customdata: any[] = []; // Store extra data (impact display)

    // Root
    const rootId = 'Portfolio';
    ids.push(rootId);
    labels.push(t('portfolio'));
    parents.push('');
    values.push(0); // Will be sum of children
    colors.push(0);
    customdata.push({ impact: 0, weight: 0 });

    // Calculate global range for colorscale to ensure 0 is white/neutral
    let maxAbsImpact = 0;

    Object.entries(data).forEach(([sectorName, stat]) => {
      const id = sectorName;
      ids.push(id);
      labels.push(sectorName);
      parents.push(rootId);
      values.push(stat.weight);
      colors.push(stat.impact);
      customdata.push({ impact: stat.impact, weight: stat.weight });

      if (Math.abs(stat.impact) > maxAbsImpact) maxAbsImpact = Math.abs(stat.impact);
    });

    if (maxAbsImpact === 0) maxAbsImpact = 0.01;

    // Add dummy root value (sum of weights)
    values[0] = values.slice(1).reduce((a, b) => a + b, 0);

    setChartData([{
      type: 'treemap',
      ids: ids,
      labels: labels,
      parents: parents,
      values: values,
      marker: {
        colors: colors,
        center: 0,
        // Refined colorscale using standard Tailwind colors:
        // Emerald-500: #10b981 (Negative)
        // Slate-50: #f8fafc (Neutral)
        // Rose-500: #f43f5e (Positive)
        colorscale: [
          [0, '#10b981'],
          [0.5, '#f8fafc'],
          [1, '#f43f5e']
        ],
        cmid: 0,
        cmin: -maxAbsImpact,
        cmax: maxAbsImpact,
        line: { width: 1, color: '#f1f5f9' }, // slate-100 for cleaner separation
        pad: { t: 0, l: 0, r: 0, b: 0 }
      },
      texttemplate: "<span style='font-size:14px;font-weight:700'>%{label}</span><br><span style='font-size:12px;opacity:0.8'>%{customdata.weight:.2f}%</span>",
      hovertemplate: `
                <div style='border-radius:8px; background:white; padding:8px;'>
                    <b style='font-size:14px; color:#334155'>%{label}</b><br>
                    <span style='color:#64748b'>Weight:</span> <b>%{value:.2f}%</b><br>
                    <span style='color:#64748b'>Impact:</span> <b>%{color:+.2f}%</b>
                </div>
                <extra></extra>
            `,
      branchvalues: 'total',
      // Use system-ui font stack
      textfont: { family: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif', color: '#1e293b' },
      tiling: { packing: 'squarify', pad: 2 }
    }]);

  }, [data, t]);


  // Detail Panel Logic
  const selectedSectorData = selectedSector ? data[selectedSector] : null;
  const sortedSubItems = useMemo(() => {
    if (!selectedSectorData?.sub) return { contributors: [], detractors: [] };

    const items = Object.entries(selectedSectorData.sub).map(([name, stat]) => ({
      name,
      ...stat
    }));

    // Sort by impact
    const contributors = items.filter(i => i.impact > 0).sort((a, b) => b.impact - a.impact).slice(0, 5);
    const detractors = items.filter(i => i.impact < 0).sort((a, b) => a.impact - b.impact).slice(0, 5); // Most negative first

    return { contributors, detractors };
  }, [selectedSectorData]);

  return (
    <div className="mt-6 relative min-h-[420px] lg:h-[420px] w-full select-none">
      {/* Backdrop for mobile drawer */}
      {selectedSector && (
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[60] lg:hidden transition-opacity duration-300"
          onClick={() => setSelectedSector(null)}
        />
      )}

      {/* Header / Legend Area */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 px-1 gap-3">
        <div className="flex flex-col">
          <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            {t('performanceAttribution')}
          </h3>
          <span className="text-[10px] text-slate-400 font-mono mt-0.5">
            {t('sizeIsWeight')} • {t('colorIsImpact')}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-medium text-slate-500">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-emerald-500"></div>
            <span>Detract</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-rose-500"></div>
            <span>Contribute</span>
          </div>
        </div>
      </div>

      {/* Treemap Container */}
      <div className={`relative w-full h-[360px] rounded-xl overflow-hidden border border-slate-100 shadow-sm bg-white transition-all duration-300 ${selectedSector ? 'lg:mr-[320px] lg:pr-[320px]' : ''}`}>
        <div className={`w-full h-full transition-all duration-300 ${selectedSector ? 'lg:w-[calc(100%-310px)]' : 'w-full'}`}>
          {chartData.length > 0 && (
            <Plot
              data={chartData}
              layout={{
                margin: { t: 0, l: 0, r: 0, b: 0 },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: {
                  family: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
                },
                autosize: true,
                clickmode: 'event',
                hovermode: 'closest',
                hoverlabel: {
                  bgcolor: '#ffffff',
                  bordercolor: '#e2e8f0',
                  font: { family: 'ui-sans-serif, system-ui, sans-serif', size: 12, color: '#334155' }
                }
              }}
              style={{ width: '100%', height: '100%' }}
              config={{ displayModeBar: false, responsive: true }}
              onClick={(e: any) => {
                if (e.points && e.points[0]) {
                  const label = e.points[0].label;
                  if (label !== 'Portfolio') {
                    setSelectedSector(label);
                  }
                }
              }}
            />
          )}
        </div>
      </div>

      {/* Drill-down Drawer / Slide-over */}
      <div
        className={`fixed inset-x-0 bottom-0 lg:absolute lg:inset-y-0 lg:left-auto lg:right-0 w-full lg:w-[300px] h-[70vh] lg:h-full glass-panel border-t lg:border-t-0 lg:border-l border-slate-200/60 shadow-2xl z-[70] transition-transform duration-300 ease-out transform ${selectedSector ? 'translate-y-0 lg:translate-x-0' : 'translate-y-full lg:translate-y-0 lg:translate-x-[110%]'} rounded-t-2xl lg:rounded-t-none lg:rounded-xl overflow-hidden flex flex-col bg-white/95 backdrop-blur-md`}
      >
        {selectedSector && selectedSectorData && (
          <>
            {/* Drawer Drag Handle (Mobile only) */}
            <div className="w-12 h-1 bg-slate-200 rounded-full mx-auto mt-3 mb-1 lg:hidden" />
            
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-100 flex justify-between items-start bg-white/50">
              <div>
                <h4 className="font-bold text-lg text-slate-800 leading-tight tracking-tight">{selectedSector}</h4>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[10px] font-mono font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                    Weight: {selectedSectorData.weight.toFixed(2)}%
                  </span>
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${selectedSectorData.impact >= 0 ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'}`}>
                    Impact: {selectedSectorData.impact > 0 ? '+' : ''}{selectedSectorData.impact.toFixed(2)}%
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedSector(null)}
                className="p-1.5 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-4">
              {/* Top Contributors */}
              {sortedSubItems.contributors.length > 0 && (
                <div>
                  <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5 pl-1">
                    <TrendingUp className="w-3 h-3 text-rose-500" />
                    <span>Top Contributors</span>
                  </h5>
                  <div className="space-y-1.5">
                    {sortedSubItems.contributors.map(item => (
                      <div key={item.name} className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-100 shadow-sm hover:border-slate-200 transition-colors">
                        <div className="flex flex-col min-w-0">
                          <span className="text-xs font-bold text-slate-700 truncate pr-2">{item.name}</span>
                          <span className="text-[9px] text-slate-400 font-mono">W: {item.weight.toFixed(2)}%</span>
                        </div>
                        <span className="text-xs font-bold font-mono text-rose-600 shrink-0">+{item.impact.toFixed(3)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Top Detractors */}
              {sortedSubItems.detractors.length > 0 && (
                <div>
                  <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5 pl-1">
                    <TrendingDown className="w-3 h-3 text-emerald-500" />
                    <span>Top Detractors</span>
                  </h5>
                  <div className="space-y-1.5">
                    {sortedSubItems.detractors.map(item => (
                      <div key={item.name} className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-100 shadow-sm hover:border-slate-200 transition-colors">
                        <div className="flex flex-col min-w-0">
                          <span className="text-xs font-bold text-slate-700 truncate pr-2">{item.name}</span>
                          <span className="text-[9px] text-slate-400 font-mono">W: {item.weight.toFixed(2)}%</span>
                        </div>
                        <span className="text-xs font-bold font-mono text-emerald-600 shrink-0">{item.impact.toFixed(3)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Empty State */}
              {sortedSubItems.contributors.length === 0 && sortedSubItems.detractors.length === 0 && (
                <div className="text-center py-8 opacity-50 text-xs text-slate-400">
                  No detailed attribution data
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}