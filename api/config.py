# config.py
import json
import os

CONFIG_FILE = "config.json"
STATUS_FILE = "data_status.json"

RELATIVE_OFFSETS = {
    "대표자": 1, "사업자번호": 2, "지역": 3, "시평": 4, 
    "3년 실적": 5, "5년 실적": 6, "부채비율": 7, "유동비율": 8, 
    "영업기간": 9, "신용평가": 10, "여성기업": 11, "고용자수": 12, 
    "일자리창출": 13, "품질평가": 14, "비고": 15
}

# 업종별 평균 비율!!
INDUSTRY_AVERAGES = {
    # 2024년 한국은행 기업경영분석 (E35-36, J61-63 기준)
    "전기": {"부채비율": 124.41, "유동비율": 142.58},
    "통신": {"부채비율": 124.03, "유동비율": 140.06},
    "소방": {"부채비율": 110.08, "유동비율": 139.32}
}
# [이 코드를 추가하세요]
CONSORTIUM_RULES = {
    "행안부": {
        "30억미만": {
            "name": "행안부 30억미만",
            "use_duration_score": False, # 30억 미만은 영업기간 점수 미사용
            "performance_method": "ratio_table",
            "performance_base_key": "estimation_price",
            "performance_multiplier": 0.8,
            "debt_score_table_id": "haeng_30_down_debt",
            "current_score_table_id": "haeng_30_down_current",
            "credit_score_table_id": "haeng_default_credit",
            "performance_score_table_id": "haeng_default_performance",
            "debt_base_score": 4.8,
            "current_base_score": 4.2,
            # [핵심 추가] 실적 점수 관련 규칙
            "performance_base_score": 1.0 # 20% 미만일 때의 점수
        },
        "30억이상": {
            "name": "행안부 30억이상",
            "performance_multiplier": 0.8 ,
            "performance_method": "ratio_table", #비율제 -> 80% 이상은 15점 .. 이런식
            "performance_base_key": "estimation_price", #추정금액
            "use_duration_score": True,
            "duration_score_table_id": "haeng_30_up_duration",
            "debt_score_table_id": "haeng_30_up_debt",
            "current_score_table_id": "haeng_30_up_current",
            "debt_base_score": 4.8,
            "current_base_score": 4.2,
            # [핵심 추가] 실적 점수 관련 규칙
            "performance_score_table_id": "haeng_default_performance",
            "performance_base_score": 1.0
        },
        # 추후 50억 추가 예정
        # "50억이상": {
        #     "name": "행안부 50억이상",
        #     "performance_multiplier": 1.0,  # 예시
        #     "use_duration_score": True,
        #     "debt_score_table_id": "haeng_50_up_debt",  # 50억 이상 전용 점수표 연결
        #     "current_score_table_id": "haeng_50_up_current",
        #     "performance_score_table_id": "haeng_default_performance",
        #     "debt_base_score": 4.5,  # 예시
        #     "current_base_score": 4.0,  # 예시
        #     "performance_base_score": 1.0
        # }
    },
    # [핵심] "조달청"은 행안부와 동등한 레벨의 새로운 키가 되어야 합니다.
    "조달청": {
        "50억미만": {
            "name": "조달청 50억미만",
            "performance_multiplier": 1.0,
            "use_duration_score": False,
            "performance_method": "direct_formula_v1", # 시공경험 점수를 비율제로 할건지 직접 계산할건지 정함 -> 실적계수×15 이런것.
            "performance_base_key": "notice_base_amount", # 기초금액, 추정금액 중 기준으로 할 금액 선정
            "debt_score_table_id": "jodal_50_down_debt",
            "current_score_table_id": "jodal_50_down_current",
            "performance_score_table_id": "jodal_default_performance",
            "credit_score_table_id": "jodal_default_credit",
            "debt_base_score": 4.2,
            "current_base_score": 4.0,
            "performance_base_score": 10.0
        }
    }
}



BUSINESS_SCORE_TABLES = {
    # --- 행안부 점수표 ---
    "haeng_30_down_debt": [  # 행안부 30억 미만 부채비율
        (50, 8.0), (75, 7.2), (100, 6.4), (125, 5.6), (float('inf'), 4.8)
    ],
    "haeng_30_down_current": [ # 행안부 30억 미만 유동비율
        (150, 7.0), (120, 6.3), (100, 5.6), (70, 4.9), (float('inf'), 4.2)
    ],
    "haeng_30_up_debt": [  # 행안부 30억 이상 부채비율 (예시)
        (50, 7.0), (75, 6.3), (100, 5.6), (125, 4.9), (float('inf'), 4.2)
    ],
    "haeng_30_up_current": [  # 행안부 30억 이상 유동비율 (예시)
        (150, 7.0), (120, 6.3), (100, 5.6), (70, 4.9), (float('inf'), 4.2)
    ],
    "haeng_50_up_debt": [  # 행안부 50억 이상 부채비율 (예시)
        (50, 10.0), (75, 9.3), (100, 8.6), (125, 7.9), (float('inf'), 7.2)
    ],
    "haeng_50_up_current": [  # 행안부 50억 이상 유동비율 (예시)
        (150, 10.0), (120, 9.3), (100, 8.6), (70, 7.9), (float('inf'), 7.2)
    ],

    # --- 조달청 점수표 ---
    "jodal_50_down_debt": [
        (50, 7.0), (75, 6.2), (100, 5.4), (125, 4.6), (float('inf'), 3.8)
    ],
    "jodal_50_down_current": [
        (150, 7.0), (120, 6.2), (100, 5.4), (70, 4.6), (float('inf'), 3.8)
    ]
}

# ▼▼▼▼▼ [추가] 영업기간 전용 점수표 ▼▼▼▼▼
DURATION_SCORE_TABLES = {
    "haeng_30_up_duration": [ # 행안부 30억 이상 영업기간 (3점 만점 예시)
        (20, 3.0),    # 20년 이상
        (15, 2.8),    # 15년 이상
        (10, 2.5),    # 10년 이상
        (5, 2.2)      # 5년 이상
    ]
}






# [신규] 신용평가 등급별 점수표를 여기에 정의합니다.
CREDIT_RATING_SCORES = {
    "haeng_default_credit": { # 행안부 공용
        'AAA': 15.0, 'AA+': 15.0, 'AA0': 15.0, 'AA-': 15.0,
        'A+': 15.0, 'A0': 15.0, 'A-': 15.0,
        'BBB+': 15.0, 'BBB0': 15.0, 'BBB-': 15.0,
        'BB+': 15.0, 'BB0': 15.0,
        'BB-': 14.0,
        'B+': 13.0, 'B0': 13.0, 'B-': 13.0,
        'CCC+': 10.0, 'CCC0': 10.0, 'CCC-': 10.0,
        'CC': 10.0, 'C': 10.0, 'D': 10.0
    },
    "jodal_default_credit": {  # 조달청 공용 -> 수정예정
        'AAA': 15.0, 'AA+': 15.0, 'AA0': 15.0, 'AA-': 15.0,
        'A+': 15.0, 'A0': 15.0, 'A-': 15.0,
        'BBB+': 15.0, 'BBB0': 15.0, 'BBB-': 15.0,
        'BB+': 15.0, 'BB0': 15.0,
        'BB-': 14.0,
        'B+': 13.0, 'B0': 13.0, 'B-': 13.0,
        'CCC+': 10.0, 'CCC0': 10.0, 'CCC-': 10.0,
        'CC': 10.0, 'C': 10.0, 'D': 10.0
    }
}



# 이 부분은 업체 조회 시 빨간색 강조 표시에만 사용됩니다.
RATIO_THRESHOLDS = {
    "전기": {"부채비율_초과": 62.02, "유동비율_이하": 213.87},
    "통신": {"부채비율_초과": 62.01, "유동비율_이하": 210.09},
    "소방": {"부채비율_초과": 55.54, "유동비율_이하": 208.98}
}

PERFORMANCE_SCORE_TABLE = {
    "haeng_default_performance": [  # 행안부 공용 실적 점수표
        (80, 15.0), (70, 13.0), (60, 11.0), (50, 9.0),
        (40, 7.0), (30, 5.0), (20, 3.0), (float('inf'), 1.0)
    ],
    # "jodal_default_performance": [  # 조달청 공용 실적 점수표
    #     (100, 15.0), (90, 14.0), (80, 13.0),
    #     (70, 12.0), (60, 11.0)
    # ]
}




def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config_data = {}

    # 기본값 설정
    defaults = {
        "전기": "", "통신": "", "소방": "",
        "api_service_key": "Sd1XTZC1ETtjjiuT7EtadyY6HwOmSxV15ku3GMafe7bF0L+ArOici8fbizdiQaermVXmDuywljzKFW8WJpeufg==" # API 서비스 키 기본값
    }
    
    # 설정 파일에 없는 키가 있으면 기본값으로 채워줌
    for key, value in defaults.items():
        config_data.setdefault(key, value)
        
    return config_data


# 이하 함수들은 수정 없음...
def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# def load_data_status():
#     try:
#         with open(STATUS_FILE, 'r', encoding='utf-8') as f:
#             return json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError): return {}
# def save_data_status(data):
#     with open(STATUS_FILE, 'w', encoding='utf-8') as f:
#         json.dump(data, f, indent=4, ensure_ascii=False)