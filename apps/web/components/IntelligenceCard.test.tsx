import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import IntelligenceCard from './IntelligenceCard'

// Mock data
const mockItem: any = {
    id: 1,
    source: 'google',
    source_id: '123',
    title: 'Test Title',
    url: 'http://example.com',
    content: 'Test Content',
    summary: 'Mock Summary',
    sentiment: 'Bullish',
    urgency_score: 9,
    actionable_advice: 'Buy now',
    timestamp: new Date().toISOString(),
    author: 'Test Author',
    market_implication: {},
    original_content: 'Content',
    gold_price_snapshot: 2000,
    price_1h: 0.1,
    price_24h: 0.5
};

const mockGetLocalizedText = jest.fn((text: string, locale: string) => text);
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
