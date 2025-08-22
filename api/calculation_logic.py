# calculation_logic.py
import utils
# calculation_logic.py

from config import INDUSTRY_AVERAGES, CREDIT_RATING_SCORES, CONSORTIUM_RULES, BUSINESS_SCORE_TABLES, PERFORMANCE_SCORE_TABLE, DURATION_SCORE_TABLES
import re
from datetime import datetime


def _is_credit_rating_valid(rating_str, announcement_date):
    """
    신용평가 문자열을 검증하여 상세 상태('유효', '기간만료' 등)를 반환합니다.
    """
    if not rating_str or not isinstance(rating_str, str) or rating_str.strip() == "":
        return "자료없음"
    
    match = re.search(r'\((\d{2,4}[./-]\d{1,2}[./-]\d{1,2})~(\d{2,4}[./-]\d{1,2}[./-]\d{1,2})\)', rating_str.replace(" ", ""))
    if not match:
        return "형식오류"

    try:
        start_date_str, end_date_str = match.groups()
        
        # 날짜 구분자(., /, -)에 상관없이 파싱
        def parse_date(date_str):
            for fmt in ('%Y.%m.%d', '%y.%m.%d', '%Y/%m/%d', '%y/%m/%d', '%Y-%m-%d', '%y-%m-%d'):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            raise ValueError("날짜 형식이 올바르지 않습니다.")

        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        
        if start_date <= announcement_date <= end_date:
            return "유효"
        else:
            return "기간만료"
        
    except (ValueError, TypeError):
        return "형식오류"


def _get_score_from_table(value, table, lower_is_better=True):
    if value is None: return 0.0
    for threshold, score in table:
        if lower_is_better and value < threshold: return score
        if not lower_is_better and value >= threshold: return score

    # ▼▼▼▼▼ [수정] 아래 한 줄을 추가하거나 기존 return 0.0을 대체 ▼▼▼▼▼
    # 루프가 끝났다는 것은 마지막 등급이라는 의미이므로, 테이블의 마지막 점수를 반환
    return table[-1][1] if table else 0.0

def _calculate_debt_ratio_score(ratio_percentage, ruleset):
    table_id = ruleset.get("debt_score_table_id", "default_debt")
    score_table = BUSINESS_SCORE_TABLES.get(table_id, [])
    base_score = ruleset.get("debt_base_score", 0.0)
    score = _get_score_from_table(ratio_percentage, score_table, lower_is_better=True)
    return score if score > 0 else base_score

def _calculate_current_ratio_score(ratio_percentage, ruleset):
    table_id = ruleset.get("current_score_table_id", "default_current")
    score_table = BUSINESS_SCORE_TABLES.get(table_id, [])
    base_score = ruleset.get("current_base_score", 0.0)
    score = _get_score_from_table(ratio_percentage, score_table, lower_is_better=False)
    return score if score > 0 else base_score


def _get_score_from_credit_rating(rating_str, ruleset):
    """규칙(ruleset)에 명시된 ID를 보고 올바른 신용평가 점수표에서 점수를 가져옵니다."""
    if not rating_str or not isinstance(rating_str, str): return 0.0

    # 1. 규칙(ruleset)에서 사용할 점수표 ID를 가져옵니다.
    table_id = ruleset.get("credit_score_table_id")
    if not table_id: return 0.0

    # 2. config의 CREDIT_RATING_SCORES에서 해당 점수표를 찾습니다.
    score_table = CREDIT_RATING_SCORES.get(table_id, {})

    try:
        # .split()은 띄어쓰기, 줄바꿈, 탭 등 모든 공백을 기준으로 문자열을 나눕니다.
        rating = rating_str.split()[0].strip().upper()
    except IndexError:
        # 혹시 모를 예외 처리 (빈 문자열 등)
        return 0.0

    return score_table.get(rating, 0.0)

# [calculate_business_score 함수를 이 코드로 통째로 교체하세요]
def calculate_business_score(company_data, industry_type, announcement_date, ruleset):
    """
    [최종 수정] 개별 회사의 경영상태 점수를 계산합니다. (항목별 데이터 상태 우선 검증)
    """
    default_result = {'total': 0.0, 'debt_score': 0.0, 'current_score': 0.0, 
                      'credit_score': 0.0, 'basis': "오류", 'credit_valid': "자료없음",  'duration_score': 0.0}

    if not company_data or not industry_type or industry_type not in INDUSTRY_AVERAGES:
        return default_result

    data_status = company_data.get('데이터상태', {})
    
    # [핵심] '부채비율'과 '유동비율'의 상태를 각각 확인
    debt_status = data_status.get('부채비율', '미지정')
    current_status = data_status.get('유동비율', '미지정')

    # 둘 중 하나라도 '최신'이 아니면 경영점수 계산을 하지 않음
    if debt_status != "최신" or current_status != "최신":
        default_result['basis'] = "만료된 재무 데이터"
        credit_rating_str = company_data.get("신용평가")
        default_result['credit_valid'] = _is_credit_rating_valid(credit_rating_str, announcement_date)
        return default_result

    # --- 이하 로직은 데이터가 '최신'일 경우에만 실행됩니다 ---
    try:
        company_debt_ratio = float(str(company_data.get("부채비율", "0")).replace('%', '').strip())
        company_current_ratio = float(str(company_data.get("유동비율", "0")).replace('%', '').strip())
    except (ValueError, TypeError):
        return {**default_result, 'basis': "데이터 오류"}

    industry_avgs = INDUSTRY_AVERAGES[industry_type]
    avg_debt_ratio = industry_avgs.get("부채비율", 100.0)
    avg_current_ratio = industry_avgs.get("유동비율", 100.0)
    debt_ratio_vs_industry = ((company_debt_ratio * 100) / avg_debt_ratio) if avg_debt_ratio else 0
    current_ratio_vs_industry = ((company_current_ratio * 100) / avg_current_ratio) if avg_current_ratio else 0
    
    debt_score = _calculate_debt_ratio_score(debt_ratio_vs_industry, ruleset)
    current_score = _calculate_current_ratio_score(current_ratio_vs_industry, ruleset)

    # ▼▼▼▼▼ 디버깅용 print문 추가 ▼▼▼▼▼
    print(f"[디버깅] 경영상태 점수 -> 부채: {debt_score}, 유동: {current_score}")

    # --- [핵심 추가] 영업기간 점수 계산 ---
    duration_score = 0.0
    if ruleset.get("use_duration_score"):
        try:
            # 1. 영업기간 데이터 가져오기 (문자열에서 숫자만 추출)
            duration_str = str(company_data.get("영업기간", "0"))
            company_duration = float(re.sub(r'[^0-9.]', '', duration_str))

            # 2. 사용할 점수표 ID 가져오기
            table_id = ruleset.get("duration_score_table_id")
            score_table = DURATION_SCORE_TABLES.get(table_id, [])

            # 3. 점수 계산
            duration_score = _get_score_from_table(company_duration, score_table, lower_is_better=False)
        except (ValueError, TypeError):
            duration_score = 0.0

    # 재무비율과 영업기간 점수를 합산
    ratio_based_score = debt_score + current_score + duration_score


    credit_rating_str = company_data.get("신용평가")
    credit_based_score = _get_score_from_credit_rating(credit_rating_str, ruleset)
    credit_status = _is_credit_rating_valid(credit_rating_str, announcement_date)

    final_score = 0
    basis = ""

    if credit_status == '유효' and credit_based_score > ratio_based_score:
        final_score = credit_based_score
        basis = "신용평가"
    else:
        final_score = ratio_based_score
        basis = "재무비율"

    return {
        'debt_score': debt_score, 
        'current_score': current_score,
        'credit_score': credit_based_score,
        'duration_score': duration_score,
        'credit_valid': credit_status,
        'total': final_score, 
        'basis': basis
    }


def _calculate_performance_score(ruleset, total_performance, base_amount):
    """
    규칙(ruleset)에 명시된 계산 방식에 따라 시공경험 점수와 비율을 함께 반환합니다.
    """
    method = ruleset.get("performance_method")

    # --- 방식 1: 비율을 계산하여 점수표에서 찾아오는 방식 ---
    if method == "ratio_table":
        ratio = (total_performance / base_amount) * 100 if base_amount > 0 else 0
        table_id = ruleset.get("performance_score_table_id")
        score_table = PERFORMANCE_SCORE_TABLE.get(table_id, [])
        base_score = ruleset.get("performance_base_score", 0.0)

        score = _get_score_from_table(ratio, score_table, lower_is_better=False)
        final_score = score if score > 0 else base_score

        # [수정] 최종 점수와 함께 계산된 비율(ratio)도 반환
        return final_score, ratio

    # --- 방식 2: 직접 수식을 통해 계산하는 방식 ---
    elif method == "direct_formula_v1":
        params = ruleset.get("performance_params", {})
        multiplier = params.get("base_multiplier", 1.0)
        max_score = params.get("max_score", 15.0)

        score = (total_performance / (base_amount * multiplier)) * max_score
        final_score = min(score, max_score)  # 만점을 넘을 수 없도록 제한

        # [수정] 화면 표시를 위한 역산된 비율과 함께 점수 반환
        equivalent_ratio = (final_score / max_score) * 100 if max_score > 0 else 0
        print(f"[디버깅] 시공경험 점수 -> {final_score}")
        return final_score, equivalent_ratio


    # [수정] 정의되지 않은 방식일 경우 (점수, 비율) 형식으로 0.0을 반환
    return 0.0, 0.0


def calculate_consortium(companies_data, price_data, announcement_date, rule_info, sipyung_info, region_limit):
    try:
        ruleset = CONSORTIUM_RULES[rule_info[0]][rule_info[1]]
    except KeyError:
        print(f"오류: {rule_info}에 해당하는 규칙을 찾을 수 없습니다."); return None

    if not companies_data or not price_data: return None

    # --- 1. 계산에 필요한 기준금액(base_amount)을 먼저 결정 ---
    base_key = ruleset.get("performance_base_key", "estimation_price") # 기본값은 추정가격
    base_amount_for_calc = price_data.get(base_key, 0)


    detailed_results = []
    for comp in companies_data:
        company_info = comp.get('data', {})
        share = comp.get('share', 0)
        industry_type = comp.get('source_type', '전기')
        business_score_details = calculate_business_score(company_info, industry_type, announcement_date, ruleset)
        detailed_results.append({
            "role": comp.get('role'),
            "name": company_info.get("검색된 회사", ""),
            "data": company_info,
            "business_score_details": business_score_details,
            "performance_5y": utils.parse_amount(company_info.get("5년 실적", 0)) or 0,
            "share": share
        })

    # --- 점수 계산 (기존과 동일) ---
    final_business_score = sum(
        (r['business_score_details'].get('total', 0) * r.get('share', 0)) for r in detailed_results)

    # 1. 컨소시엄의 총 실적액(total_weighted_performance)을 계산
    total_weighted_performance = sum([(r.get('performance_5y', 0) * r.get('share', 0)) for r in detailed_results])

    # 3. 위에서 구한 비율을 가지고 cofnig.py의 점수표에서 해당하는 점수를 가져와서 담음.
    final_performance_score, performance_ratio = _calculate_performance_score(ruleset, total_weighted_performance,
                                                                              base_amount_for_calc)

    # --- 3. 모든 검증 로직 ---
    # [수정] 단독입찰 실적 조건(performance_target)도 올바른 기준금액으로 계산
    performance_target = base_amount_for_calc * ruleset.get('performance_multiplier', 1.0)




    # 1. 단독입찰 검증 (시평액 조건 추가)
    solo_bid_results = []
    sipyung_is_limited = sipyung_info.get("is_limited", False)
    sipyung_limit_amount = sipyung_info.get("limit_amount", 0)

    for comp_detail in detailed_results:
        company_name = comp_detail.get('name', '')
        performance_5y = comp_detail.get('performance_5y', 0)
        company_region = comp_detail.get('data', {}).get('지역', '')
        sipyung_amount = utils.parse_amount(str(comp_detail['data'].get("시평", 0))) or 0

        # 조건 1: 실적
        perf_ok = performance_5y >= performance_target
        # 조건 2: 지역
        region_ok = True
        if region_limit != "전체" and region_limit not in company_region:
            region_ok = False
        # [핵심] 조건 3: 시평액
        sipyung_ok = True
        if sipyung_is_limited and sipyung_amount < sipyung_limit_amount:
            sipyung_ok = False

        # 최종 판정
        if perf_ok and region_ok and sipyung_ok:
            is_possible = True
            reason = "실적, 지역, 시평액 모두 충족"
        else:
            is_possible = False
            reasons = []
            if not perf_ok:
                reasons.append(f"실적 부족 (필요: {performance_target:,.0f}원)")
            if not region_ok:
                reasons.append(f"지역 불일치 (필요: {region_limit})")
            if not sipyung_ok:
                reasons.append(f"시평액 부족 (필요: {sipyung_limit_amount:,.0f}원)")
            reason = ", ".join(reasons)

        solo_bid_results.append({"name": company_name, "role": comp_detail.get('role'), "possible": is_possible, "reason": reason})

    # 2. 시평액 제한 (컨소시엄 전체) 검증 (기존과 동일)
    sipyung_check_result = {"passed": True, "message": "시평액 제한 없음"}
    if sipyung_info.get("is_limited"):
        limit_amount = sipyung_info.get("limit_amount", 0)
        method = sipyung_info.get("method", "비율제")
        if method == "비율제": eval_sipyung = sum((utils.parse_amount(str(r['data'].get("시평", 0))) or 0) * (r.get('share', 0) / 100.0) for r in detailed_results)
        else: eval_sipyung = sum(utils.parse_amount(str(r['data'].get("시평", 0))) or 0 for r in detailed_results)
        if eval_sipyung < limit_amount:
            sipyung_check_result["passed"] = False; sipyung_check_result["message"] = f"시평액 미충족 ({method}) - 필요: {limit_amount:,.0f}원, 평가액: {eval_sipyung:,.0f}원"
        else:
            sipyung_check_result["passed"] = True; sipyung_check_result["message"] = f"시평액 충족 ({method}) - 평가액: {eval_sipyung:,.0f}원, 필요: {limit_amount:,.0f}원"

    # 3. 개별 업체 시평액 검증 (30억 이상) (기존과 동일)
    individual_sipyung_results = []
    if "30억이상" in rule_info[1]:
        tuchal_amount = sipyung_info.get("tuchal_amount", 0)
        if tuchal_amount > 0:
            for comp_detail in detailed_results:
                sipyung_amount = utils.parse_amount(str(comp_detail['data'].get("시평", 0))) or 0
                share = comp_detail.get('share', 0)
                required_amount = tuchal_amount * (share / 100.0)
                passed = sipyung_amount >= required_amount
                individual_sipyung_results.append({
                    "name": comp_detail.get('name', ''), "passed": passed,
                    "message": f"필요 공사액: {required_amount:,.0f}원, 보유 시평액: {sipyung_amount:,.0f}원"
                })

    # --- 최종 반환 (기존과 동일) ---
    return {
        "ruleset": ruleset, "company_details": detailed_results, "final_business_score": final_business_score,
        "total_weighted_performance": total_weighted_performance, "performance_ratio": performance_ratio,
        "final_performance_score": final_performance_score, "total_score": final_business_score + final_performance_score,
        "bid_score": 65, "expected_score": (final_business_score + final_performance_score) + 65,
        "solo_bid_results": solo_bid_results,
        "sipyung_check_result": sipyung_check_result,
        "individual_sipyung_results": individual_sipyung_results,
        "price_data": price_data
    }

def check_share_limit(companies_data, tuchal_amount):
    """
    각 업체의 시평액을 기반으로 참여 가능한 최대 지분율을 계산하고,
    사용자가 입력한 지분율이 이 한도를 '초과'하는지 검증합니다.
    """
    if tuchal_amount <= 0:
        return []

    results = []
    for comp_detail in companies_data:
        sipyung_amount = utils.parse_amount(str(comp_detail['data'].get("시평", 0))) or 0
        input_share = comp_detail.get('share', 0)

        # 최대 참여 가능 지분율 (%) 계산
        max_possible_share = (sipyung_amount / tuchal_amount) * 100 if tuchal_amount > 0 else 0

        # 입력한 지분율이, 회사가 감당할 수 있는 최대 지분율보다 큰가?
        is_problem = input_share > max_possible_share

        results.append({
            "name": comp_detail.get('name', ''),
            "input_share": input_share,
            "max_share": max_possible_share,
            "difference": max_possible_share - input_share,
            "is_problem": is_problem
        })

    return results
