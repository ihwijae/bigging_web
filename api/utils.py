# utils.py
import re

def parse_amount(amount_str):
    """'1억 5,000만' 같은 금액 문자열을 숫자로 변환합니다."""
    if amount_str is None or not str(amount_str).strip():
        return None
    
    s = str(amount_str).strip().replace(',', '')
    s = re.sub(r'[^\d.억만백십]', '', s)
    
    total = 0.0
    억_match = re.search(r'([\d.]+)\s*억', s)
    if 억_match:
        total += float(억_match.group(1)) * 100000000
        s = s.replace(억_match.group(0), '')
        
    만_match = re.search(r'([\d.]+)\s*만', s)
    if 만_match:
        total += float(만_match.group(1)) * 10000
        s = s.replace(만_match.group(0), '')
        
    if s:
        try:
            total += float(s)
        except ValueError:
            pass
            
    return total if total > 0 else None