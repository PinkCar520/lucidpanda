'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface AnimatedNumberProps {
    value: number | string;
    precision?: number;
    prefix?: string;
    suffix?: string;
    className?: string;
    showPlusMinus?: boolean;
}

export default function AnimatedNumber({
    value,
    precision = 0,
    prefix = '',
    suffix = '',
    className = '',
    showPlusMinus = false,
}: AnimatedNumberProps) {
    const [prevValue, setPrevValue] = useState(value);
    const [direction, setDirection] = useState<'up' | 'down'>('up');

    const numValue = typeof value === 'number' ? value : parseFloat(value as string);
    const prevNumValue = typeof prevValue === 'number' ? prevValue : parseFloat(prevValue as string);

    if (value !== prevValue) {
        if (numValue > prevNumValue) {
            setDirection('up');
        } else if (numValue < prevNumValue) {
            setDirection('down');
        }
        setPrevValue(value);
    }

    const displayValue = typeof value === 'number' 
        ? value.toFixed(precision) 
        : value;

    const formattedValue = showPlusMinus && numValue > 0 ? `+${displayValue}` : displayValue;

    return (
        <div className={`relative overflow-hidden flex tabular-nums ${className}`}>
            <AnimatePresence mode="popLayout" custom={direction}>
                <motion.span
                    key={value.toString() + suffix}
                    initial={{ y: direction === 'up' ? 15 : -15, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: direction === 'up' ? -15 : 15, opacity: 0 }}
                    transition={{ 
                        type: "spring", 
                        stiffness: 400, 
                        damping: 35,
                        mass: 0.8
                    }}
                    className="inline-block"
                >
                    {prefix}{formattedValue}{suffix}
                </motion.span>
            </AnimatePresence>
        </div>
    );
}
