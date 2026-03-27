import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import IntelligenceCard from './IntelligenceCard'
import type { Intelligence, LocalizedText } from '@/lib/db'

// Mock data
const mockItem: Intelligence = {
    id: 1,
    source_id: '123',
    url: 'http://example.com',
    content: 'Test Content',
    summary: 'Mock Summary',
    sentiment: 'Bullish',
    urgency_score: 9,
    actionable_advice: 'Buy now',
    timestamp: new Date().toISOString(),
    author: 'Test Author',
    market_implication: 'Implication',
    gold_price_snapshot: 2000,
    price_15m: 0.05,
    price_1h: 0.1,
    price_4h: 0.2,
    price_12h: 0.3,
    price_24h: 0.5
};

const mockGetLocalizedText = jest.fn((text: LocalizedText, locale: string) => {
    if (typeof text === 'string') return text;
    return text[locale] ?? '';
});
const mockT = jest.fn((key: string) => key);
const mockTSentiment = jest.fn((key: string) => key);
const mockIsBearish = false;

describe('IntelligenceCard', () => {
    it('renders intelligence summary', () => {
        render(
            <IntelligenceCard
                item={mockItem}
                style={{}}
                locale="en"
                getLocalizedText={mockGetLocalizedText}
                t={mockT}
                tSentiment={mockTSentiment}
                isBearish={mockIsBearish}
            />
        )

        expect(screen.getByText('Mock Summary')).toBeInTheDocument()
    });

    it('renders author and score', () => {
        render(
            <IntelligenceCard
                item={mockItem}
                style={{}}
                locale="en"
                getLocalizedText={mockGetLocalizedText}
                t={mockT}
                tSentiment={mockTSentiment}
                isBearish={mockIsBearish}
            />
        )
        // Check author
        expect(screen.getByText('Test Author')).toBeInTheDocument()

        // Check score text (mockT('score') returns 'score', followed by : 9)
        expect(screen.getByText(/score: 9/i)).toBeInTheDocument()
    })
});
