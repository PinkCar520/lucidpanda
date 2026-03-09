'use client';

import React, { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { authenticatedFetch } from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/Sheet';
import { AlertTriangle, ExternalLink, GitBranch, Network, Sparkles } from 'lucide-react';

type GraphNode = {
  node_id: number;
  entity_name: string;
  entity_type?: string;
};

type GraphEdge = {
  edge_id?: number;
  from_node_id?: number;
  to_node_id?: number;
  from_entity?: string;
  to_entity?: string;
  relation: string;
  strength?: number;
  confidence_score?: number;
  evidence_source_id?: string;
  intelligence_id?: number;
};

type EventGraphResponse = {
  cluster_id?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  inferences?: Array<{ explanation?: string; confidence?: number; conclusion?: string }>;
  evidence?: Array<{ id?: number; source_id?: string; title?: string; summary?: string | { zh?: string; en?: string }; source_name?: string; source_url?: string; timestamp?: string }>;
};

type EntityGraphResponse = {
  center?: GraphNode | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

type PathResponse = {
  paths: Array<{ hops: number; score: number; edges: GraphEdge[] }>;
};

type QualityResponse = {
  window_days: number;
  summary: {
    completed_count: number;
    with_relations_count: number;
    relation_item_count: number;
    relation_coverage_pct: number;
    avg_relations_per_event: number;
  };
  quality: {
    total_relation_items: number;
    malformed_items: number;
    malformed_pct: number;
    valid_direction_pct: number;
    in_vocab_items: number;
    in_vocab_pct: number;
  };
};

function GraphPreview({
  nodes,
  edges,
  selectedFrom,
  selectedTo,
  highlightedPathKeys,
  onNodeClick,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedFrom?: string;
  selectedTo?: string;
  highlightedPathKeys?: Set<string>;
  onNodeClick?: (name: string) => void;
}) {
  const width = 860;
  const height = 380;
  const radius = Math.max(90, Math.min(150, 30 + nodes.length * 3));
  const centerX = width / 2;
  const centerY = height / 2;

  const positions = useMemo(() => {
    const map = new Map<number, { x: number; y: number }>();
    nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / Math.max(nodes.length, 1);
      map.set(node.node_id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
      });
    });
    return map;
  }, [nodes, centerX, centerY, radius]);

  if (!nodes.length) {
    return <div className="text-xs text-slate-500">No graph data</div>;
  }

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
      <svg width={width} height={height} className="min-w-[860px]">
        {edges.map((edge, index) => {
          const from = edge.from_node_id ? positions.get(edge.from_node_id) : undefined;
          const to = edge.to_node_id ? positions.get(edge.to_node_id) : undefined;
          if (!from || !to) return null;
          const score = Number(edge.confidence_score ?? 50);
          const edgeKey = `${String(edge.from_entity || '').toLowerCase()}|${String(edge.to_entity || '').toLowerCase()}|${String(edge.relation || '').toLowerCase()}`;
          const isHighlighted = !!highlightedPathKeys?.has(edgeKey);
          return (
            <line
              key={`edge-${edge.edge_id ?? index}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={isHighlighted ? '#f97316' : (score >= 70 ? '#2563eb' : score >= 50 ? '#0ea5e9' : '#94a3b8')}
              strokeOpacity={isHighlighted ? 0.95 : 0.75}
              strokeWidth={isHighlighted ? 4 : Math.max(1, Math.min(3, Number(edge.strength ?? 0.6) * 3))}
            />
          );
        })}

        {nodes.map((node) => {
          const pos = positions.get(node.node_id);
          if (!pos) return null;
          const isFrom = selectedFrom?.toLowerCase() === String(node.entity_name || '').toLowerCase();
          const isTo = selectedTo?.toLowerCase() === String(node.entity_name || '').toLowerCase();
          const fill = isFrom ? '#f59e0b' : isTo ? '#8b5cf6' : '#1d4ed8';
          return (
            <g
              key={`node-${node.node_id}`}
              className={onNodeClick ? 'cursor-pointer' : ''}
              onClick={() => onNodeClick?.(node.entity_name)}
            >
              <circle cx={pos.x} cy={pos.y} r={13} fill={fill} fillOpacity={0.92} />
              <text x={pos.x} y={pos.y + 4} textAnchor="middle" fill="#fff" fontSize={10} fontWeight={700}>
                {String(node.entity_name || '?').slice(0, 2).toUpperCase()}
              </text>
              <text x={pos.x} y={pos.y + 24} textAnchor="middle" fill="#334155" fontSize={11}>
                {node.entity_name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function GraphPage() {
  const t = useTranslations('GraphMonitor');
  const { data: session } = useSession();

  const [clusterId, setClusterId] = useState('');
  const [entityName, setEntityName] = useState('Gold');
  const [fromEntity, setFromEntity] = useState('Fed');
  const [toEntity, setToEntity] = useState('Gold');
  const [qualityDays, setQualityDays] = useState('14');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [eventGraph, setEventGraph] = useState<EventGraphResponse | null>(null);
  const [entityGraph, setEntityGraph] = useState<EntityGraphResponse | null>(null);
  const [paths, setPaths] = useState<PathResponse | null>(null);
  const [quality, setQuality] = useState<QualityResponse | null>(null);
  const [showEvidenceSheet, setShowEvidenceSheet] = useState(false);
  const [selectedPathIndex, setSelectedPathIndex] = useState<number | null>(null);

  const fetchJSON = async <T,>(url: string): Promise<T> => {
    const res = await authenticatedFetch(url, session ?? null);
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json() as Promise<T>;
  };

  const loadGraphQuality = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchJSON<QualityResponse>(`/api/v1/web/graph/quality?days=${encodeURIComponent(qualityDays)}`);
      setQuality(data);
    } catch (e) {
      setError(`${t('loadFailed')}: ${String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  const loadEventGraph = async () => {
    if (!clusterId.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await fetchJSON<EventGraphResponse>(`/api/v1/web/graph/event/${encodeURIComponent(clusterId.trim())}`);
      setEventGraph(data);
    } catch (e) {
      setError(`${t('loadFailed')}: ${String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  const loadEntityGraph = async () => {
    if (!entityName.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await fetchJSON<EntityGraphResponse>(
        `/api/v1/web/graph/entity/${encodeURIComponent(entityName.trim())}?limit=80`
      );
      setEntityGraph(data);
    } catch (e) {
      setError(`${t('loadFailed')}: ${String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  const loadGraphPath = async (fromInput?: string, toInput?: string) => {
    const from = (fromInput ?? fromEntity).trim();
    const to = (toInput ?? toEntity).trim();
    if (!from || !to) return;
    try {
      setLoading(true);
      setError(null);
      const query = new URLSearchParams({
        from_entity: from,
        to_entity: to,
        max_hops: '2',
        min_confidence: '40',
      });
      const data = await fetchJSON<PathResponse>(`/api/v1/web/graph/path?${query.toString()}`);
      setPaths(data);
      setSelectedPathIndex(data.paths?.length ? 0 : null);
    } catch (e) {
      setError(`${t('loadFailed')}: ${String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleGraphNodeClick = async (name: string) => {
    const clean = String(name || '').trim();
    if (!clean) return;
    if (!fromEntity.trim() || (fromEntity.trim() && toEntity.trim())) {
      setFromEntity(clean);
      setToEntity('');
      setPaths(null);
      setSelectedPathIndex(null);
      return;
    }
    if (fromEntity.trim().toLowerCase() === clean.toLowerCase()) {
      return;
    }
    setToEntity(clean);
    await loadGraphPath(fromEntity.trim(), clean);
  };

  const highlightedPathKeys = useMemo(() => {
    if (selectedPathIndex == null || !paths?.paths?.[selectedPathIndex]) {
      return new Set<string>();
    }
    return new Set(
      (paths.paths[selectedPathIndex].edges || []).map((edge) =>
        `${String(edge.from_entity || '').toLowerCase()}|${String(edge.to_entity || '').toLowerCase()}|${String(edge.relation || '').toLowerCase()}`
      )
    );
  }, [paths, selectedPathIndex]);

  const filteredEvidence = useMemo(() => {
    const allEvidence = eventGraph?.evidence || [];
    if (selectedPathIndex == null || !paths?.paths?.[selectedPathIndex]) {
      return allEvidence;
    }
    const activePath = paths.paths[selectedPathIndex];
    const linkedIntelligenceIds = new Set<number>(
      (activePath.edges || [])
        .map((edge) => Number(edge.intelligence_id))
        .filter((id) => Number.isFinite(id) && id > 0)
    );
    const linkedSourceIds = new Set<string>(
      (activePath.edges || [])
        .map((edge) => String(edge.evidence_source_id || '').trim())
        .filter(Boolean)
    );

    if (linkedIntelligenceIds.size || linkedSourceIds.size) {
      const directMatched = allEvidence.filter((item) => {
        const itemId = Number(item.id);
        const sourceId = String(item.source_id || '').trim();
        return (Number.isFinite(itemId) && linkedIntelligenceIds.has(itemId)) || (!!sourceId && linkedSourceIds.has(sourceId));
      });
      if (directMatched.length) {
        return directMatched;
      }
    }

    const tokens = (activePath.edges || []).flatMap((edge) => [
      String(edge.from_entity || '').toLowerCase(),
      String(edge.to_entity || '').toLowerCase(),
      String(edge.relation || '').toLowerCase(),
    ]).filter(Boolean);
    if (!tokens.length) return allEvidence;

    const matched = allEvidence.filter((item) => {
      const haystack = `${item.title || ''} ${item.summary || ''}`.toLowerCase();
      return tokens.some((token) => haystack.includes(token));
    });
    return matched.length ? matched : allEvidence;
  }, [eventGraph, paths, selectedPathIndex]);

  return (
    <div className="flex flex-col p-4 md:p-6 lg:p-8 gap-6 min-h-screen">
      <div>
        <h1 className="text-2xl md:text-3xl font-black tracking-tight flex items-center gap-3">
          <Network className="w-7 h-7 text-blue-600" />
          {t('title')}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{t('subtitle')}</p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-300 bg-rose-50 dark:bg-rose-900/20 dark:border-rose-700 px-4 py-3 text-rose-700 dark:text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      <Card
        title={t('qualityTitle')}
        action={
          <div className="flex items-center gap-2">
            <Input value={qualityDays} onChange={(e) => setQualityDays(e.target.value)} className="w-20" />
            <Button size="sm" onClick={loadGraphQuality} disabled={loading}>
              {t('refresh')}
            </Button>
          </div>
        }
      >
        {quality ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
            <Badge variant="outline">{t('coverage')}: {quality.summary.relation_coverage_pct}%</Badge>
            <Badge variant="outline">{t('avgRelations')}: {quality.summary.avg_relations_per_event}</Badge>
            <Badge variant="outline">{t('inVocab')}: {quality.quality.in_vocab_pct}%</Badge>
            <Badge variant="outline">{t('directionValid')}: {quality.quality.valid_direction_pct}%</Badge>
            <Badge variant="outline">{t('malformed')}: {quality.quality.malformed_pct}%</Badge>
          </div>
        ) : (
          <Button variant="outline" onClick={loadGraphQuality} disabled={loading}>{t('loadQuality')}</Button>
        )}
      </Card>

      <Card
        title={t('eventTitle')}
        action={
          <div className="flex items-center gap-2 w-full md:w-auto">
            <Input
              value={clusterId}
              onChange={(e) => setClusterId(e.target.value)}
              placeholder={t('clusterPlaceholder')}
              className="min-w-[240px]"
            />
            <Button size="sm" onClick={loadEventGraph} disabled={loading || !clusterId.trim()}>
              {t('loadEvent')}
            </Button>
          </div>
        }
      >
        {eventGraph ? (
          <div className="space-y-4">
            <div className="flex gap-2 flex-wrap">
              <Badge variant="outline">{t('nodes')}: {eventGraph.nodes?.length || 0}</Badge>
              <Badge variant="outline">{t('edges')}: {eventGraph.edges?.length || 0}</Badge>
              <Badge variant="outline">{t('inferences')}: {eventGraph.inferences?.length || 0}</Badge>
              <Badge variant="outline">{t('evidence')}: {eventGraph.evidence?.length || 0}</Badge>
              {!!eventGraph.evidence?.length && (
                <Button size="sm" variant="outline" onClick={() => setShowEvidenceSheet(true)}>
                  {t('openEvidence')}
                </Button>
              )}
            </div>
            <GraphPreview
              nodes={eventGraph.nodes || []}
              edges={eventGraph.edges || []}
              selectedFrom={fromEntity}
              selectedTo={toEntity}
              highlightedPathKeys={highlightedPathKeys}
              onNodeClick={handleGraphNodeClick}
            />
            <div className="text-xs text-slate-500">{t('nodeClickHint')}</div>
          </div>
        ) : (
          <div className="text-sm text-slate-500">{t('emptyEvent')}</div>
        )}
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card
          title={t('entityTitle')}
          action={
            <div className="flex items-center gap-2 w-full md:w-auto">
              <Input value={entityName} onChange={(e) => setEntityName(e.target.value)} placeholder={t('entityPlaceholder')} />
              <Button size="sm" onClick={loadEntityGraph} disabled={loading || !entityName.trim()}>
                {t('query')}
              </Button>
            </div>
          }
        >
          {entityGraph ? (
            <div className="space-y-3">
              <div className="text-sm font-semibold flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-500" />
                {entityGraph.center?.entity_name || entityName}
              </div>
              <div className="flex gap-2 flex-wrap">
                <Badge variant="outline">{t('nodes')}: {entityGraph.nodes?.length || 0}</Badge>
                <Badge variant="outline">{t('edges')}: {entityGraph.edges?.length || 0}</Badge>
              </div>
              <div className="max-h-56 overflow-auto text-xs space-y-1">
                {(entityGraph.edges || []).slice(0, 20).map((edge, index) => (
                  <div key={`entity-edge-${index}`} className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/50">
                    {edge.from_entity} → {edge.to_entity} ({edge.relation})
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">{t('emptyEntity')}</div>
          )}
        </Card>

        <Card
          title={t('pathTitle')}
          action={
            <div className="flex items-center gap-2 w-full md:w-auto">
              <Input value={fromEntity} onChange={(e) => setFromEntity(e.target.value)} placeholder={t('from')} className="w-32" />
              <Input value={toEntity} onChange={(e) => setToEntity(e.target.value)} placeholder={t('to')} className="w-32" />
              <Button size="sm" onClick={loadGraphPath} disabled={loading || !fromEntity.trim() || !toEntity.trim()}>
                {t('query')}
              </Button>
            </div>
          }
        >
          {paths?.paths?.length ? (
            <div className="space-y-2">
              {paths.paths.map((path, index) => (
                <button
                  type="button"
                  key={`path-${index}`}
                  onClick={() => setSelectedPathIndex(index)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selectedPathIndex === index
                      ? 'border-orange-400 bg-orange-50/70 dark:bg-orange-900/20'
                      : 'border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <div className="text-xs mb-1 text-slate-500">
                    {t('hops')}: {path.hops} · Score: {path.score}
                    {selectedPathIndex === index ? ` · ${t('selected')}` : ''}
                  </div>
                  <div className="text-sm font-semibold flex items-center gap-1 flex-wrap">
                    <GitBranch className="w-4 h-4 text-blue-500" />
                    {path.edges.map((edge, edgeIndex) => (
                      <span key={`path-edge-${index}-${edgeIndex}`}>
                        {edge.from_entity} → {edge.to_entity} ({edge.relation}){edgeIndex < path.edges.length - 1 ? ' | ' : ''}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-sm text-slate-500">{t('emptyPath')}</div>
          )}
        </Card>
      </div>

      <Sheet open={showEvidenceSheet} onOpenChange={setShowEvidenceSheet}>
        <SheetContent className="max-w-2xl w-full">
          <SheetHeader>
            <SheetTitle>{t('evidenceTitle')}</SheetTitle>
            <SheetDescription>{t('evidenceSubtitle')}</SheetDescription>
          </SheetHeader>
          <div className="mt-4 space-y-3 max-h-[75vh] overflow-auto pr-2">
            {selectedPathIndex != null && <div className="text-xs text-slate-500">{t('evidenceFilteredHint')}</div>}
            {filteredEvidence.map((item, index) => (
              <div key={`evidence-${index}`} className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40">
                <div className="font-semibold text-sm">
                  {item.title || (typeof item.summary === 'string' ? item.summary : (item.summary?.zh || item.summary?.en)) || '--'}
                </div>
                <div className="mt-1 text-xs text-slate-500 flex flex-wrap gap-2">
                  <span>{item.source_name || '--'}</span>
                  <span>·</span>
                  <span>{item.timestamp ? new Date(item.timestamp).toLocaleString() : '--'}</span>
                </div>
                {item.source_url && (
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                  >
                    {t('openSource')}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            ))}
            {!filteredEvidence.length && <div className="text-sm text-slate-500">{t('emptyEvidence')}</div>}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
