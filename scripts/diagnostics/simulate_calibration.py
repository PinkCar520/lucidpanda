
import json
import numpy as np

def run_manual_calibration():
    # Data from 2026-02-03 Verification
    # Format: Code, Target_ETF(Optional), Est, Act
    
    # We classify them into groups based on logic
    data = [
        # Group A: High-End Equipment / Mfg (Underestimated by ~0.8%)
        {"code": "018927", "name": "南方电池", "est": 1.75, "act": 2.52, "type": "Stock"},
        {"code": "018125", "name": "永赢先进", "est": 1.71, "act": 2.41, "type": "Stock"},
        {"code": "018123", "name": "永赢数字", "est": 1.19, "act": 2.00, "type": "Stock"}, # Low confidence?
        
        # Group B: Precise (Resources/Info)
        {"code": "017193", "name": "天弘有色", "est": 3.20, "act": 3.07, "type": "Stock"},
        {"code": "023754", "name": "永赢信创", "est": 1.96, "act": 2.48, "type": "Stock"},
        {"code": "004320", "name": "前海沪港", "est": 3.45, "act": 3.90, "type": "Stock"},
        {"code": "015916", "name": "永赢医药", "est": 0.86, "act": 0.64, "type": "Stock"},
        
        # Group C: Overestimated (Top 10 too strong)
        {"code": "015790", "name": "永赢高端", "est": 5.06, "act": 4.17, "type": "Stock"},
        {"code": "011068", "name": "华宝资源", "est": 3.90, "act": 3.30, "type": "Stock"},
        {"code": "025209", "name": "永赢半导", "est": 3.19, "act": 2.38, "type": "Stock"},
        
        # Group D: ETF Feeders (Fixed by Penetration Logic already? Check assumptions)
        # Note: 023765 (5G) Est 0.91 -> Act 2.27. But Penetration Logic (ETF) gave 2.02.
        # So if Penetration is ON, error becomes 2.02 - 2.27 = -0.25 (Very Accurate).
        # We assume Penetration Logic is ACTIVE for these now.
        {"code": "023765", "name": "华夏5G", "est": 2.02, "act": 2.27, "type": "Feeder"}, # Using ETF Est
        {"code": "020274", "name": "富化工", "est": 3.80, "act": 3.70, "type": "Feeder"}, # Assume ETF performed well
        
        # Group E: INVALID (Broken)
        {"code": "002207", "name": "前海金银", "est": 0.63, "act": -2.30, "type": "Broken"},
        {"code": "022365", "name": "永赢科技", "est": 1.64, "act": -0.03, "type": "Broken"},
    ]
    
    print(f"{'Code':<8} {'Name':<10} {'Est':<6} {'Act':<6} {'Error':<6} {'Action'}")
    print("-" * 70)
    
    updates = {}
    
    for row in data:
        code = row['code']
        est = row['est']
        act = row['act']
        error = est - act # Positive = Overestimated, Negative = Underestimated
        
        action = "Keep"
        bias = 0.0
        
        if row['type'] == 'Broken':
            action = "❌ MARK INVALID (Churn)"
            # For broken funds, we might set a flag to warn user, or purely rely on official NAV history?
            # Or use a 'Momentum' factor? For now, just mark.
            
        elif row['type'] == 'Feeder':
            if abs(error) < 0.5:
                action = "✅ ETF Logic OK"
            else:
                bias = -error
                action = f"🔧 Fix {bias:+.2f}%"
                
        else:
            # Stocks
            if abs(error) < 0.5:
                action = "✅ Accurate"
            elif error < -0.5:
                # Low Estimate -> Add Bonus
                bias = -error * 0.8 # Conservative correction (80% of error)
                action = f"📈 Boost {bias:+.2f}%"
            elif error > 0.5:
                # High Estimate -> Penalty
                bias = -error * 0.8
                action = f"📉 Drag {bias:+.2f}%"

        print(f"{code:<8} {row['name']:<10} {est:<6.2f} {act:<6.2f} {error:<6.2f} {action}")
        
        if bias != 0:
            updates[code] = round(bias, 2)
            
    print("-" * 70)
    print("Recommended Bias Adjustments (for DB/Redis):")
    print(json.dumps(updates, indent=2))
    
    return updates

if __name__ == "__main__":
    run_manual_calibration()
