import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import GraphPage from '@/app/[locale]/graph/page';

jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

jest.mock('next-auth/react', () => ({
  useSession: () => ({ data: null }),
}));

jest.mock('@/i18n/navigation', () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

jest.mock('@/lib/api-client', () => ({
  authenticatedFetch: async (url: string) => {
    if (url.startsWith('/api/v1/web/graph/event/')) {
      return {
        ok: true,
        json: async () => ({
          cluster_id: 'cluster-1',
          nodes: [
            { node_id: 1, entity_name: 'Fed' },
            { node_id: 2, entity_name: 'Gold' },
          ],
          edges: [
            {
              edge_id: 101,
              from_node_id: 1,
              to_node_id: 2,
              from_entity: 'Fed',
              to_entity: 'Gold',
              relation: 'rate_hike',
              confidence_score: 70,
              intelligence_id: 9001,
              evidence_source_id: 'src-1',
            },
          ],
          evidence: [
            {
              id: 9001,
              source_id: 'src-1',
              title: 'Fed signal',
              source_name: 'Reuters',
              timestamp: '2026-03-09T12:00:00Z',
            },
          ],
          inferences: [],
        }),
      };
    }
    if (url.startsWith('/api/v1/web/graph/path?')) {
      return {
        ok: true,
        json: async () => ({
          paths: [
            {
              hops: 1,
              score: 70,
              edges: [
                {
                  from_entity: 'Fed',
                  to_entity: 'Gold',
                  relation: 'rate_hike',
                  confidence_score: 70,
                  intelligence_id: 9001,
                  evidence_source_id: 'src-1',
                },
              ],
            },
          ],
        }),
      };
    }
    if (url.startsWith('/api/v1/web/graph/quality?')) {
      return {
        ok: true,
        json: async () => ({
          window_days: 14,
          summary: {
            completed_count: 10,
            with_relations_count: 8,
            relation_item_count: 20,
            relation_coverage_pct: 80,
            avg_relations_per_event: 2.5,
          },
          quality: {
            total_relation_items: 20,
            malformed_items: 1,
            malformed_pct: 5,
            valid_direction_pct: 96,
            in_vocab_items: 18,
            in_vocab_pct: 90,
          },
        }),
      };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  },
}));

describe('GraphPage interactions', () => {
  it('supports event load, path query, and evidence reverse trace', async () => {
    render(<GraphPage />);

    fireEvent.change(screen.getByPlaceholderText('clusterPlaceholder'), { target: { value: 'cluster-1' } });
    fireEvent.click(screen.getByText('loadEvent'));

    await waitFor(() => expect(screen.getByText('openEvidence')).toBeInTheDocument());
    fireEvent.click(screen.getAllByText('query')[1]);

    await waitFor(() => expect(screen.getByText(/selected/i)).toBeInTheDocument());
    fireEvent.click(screen.getByText('openEvidence'));

    const evidenceCard = await screen.findByText('Fed signal');
    fireEvent.click(evidenceCard);

    await waitFor(() => {
      const hitTag = screen.getByText(/matchedEdge/i);
      expect(hitTag.textContent).toContain('%');
    });
  });
});
