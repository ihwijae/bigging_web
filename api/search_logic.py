# search_logic.py
import re
import logging
from openpyxl import load_workbook
from openpyxl.styles.colors import Color
from .config import RELATIVE_OFFSETS
from .utils import parse_amount

# --- 로깅 설정 추가 ---
# 프로그램 실행 위치에 'logs' 폴더를 만들고 그 안에 로그 파일을 기록합니다.
import os

log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logging.basicConfig(filename=os.path.join(log_dir, 'search_errors.log'),
                    level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# --------------------

def clean_text(text):
    """정규표현식을 사용하여 텍스트를 빠르게 정리합니다."""
    if not isinstance(text, str):
        return text
    # 눈에 보이지 않는 제어 문자(ASCII 0-31, 127)를 공백으로 바꿉니다.
    cleaned_text = re.sub(r'[\s\x00-\x1F\x7F]+', ' ', text)
    return cleaned_text.strip()


def get_status_from_color(color_obj) -> str:
    """셀의 색상 객체를 분석하여 데이터 상태 텍스트("최신" 등)로 변환합니다."""
    if not isinstance(color_obj, Color): return "미지정"
    if color_obj.type == 'theme':
        if color_obj.theme == 6: return "최신"
        if color_obj.theme == 3: return "1년 경과"
        if color_obj.theme in [0, 1]: return "1년 이상 경과"
    elif color_obj.type == 'rgb':
        hex_color = color_obj.rgb.upper() if color_obj.rgb else "00000000"
        if hex_color == "FFE2EFDA": return "최신"
        if hex_color == "FFDDEBF7": return "1년 경과"
        if hex_color in ["FFFFFFFF", "00000000", "FFFDEDEC"]: return "1년 이상 경과"
    return "미지정"


def find_and_filter_companies(file_path, filters):
    all_companies = []

    try:
        workbook = load_workbook(filename=file_path, data_only=False)
    except Exception as e:
        logging.error(f"엑셀 파일 열기 실패: {file_path}, 오류: {e}")
        return [{"오류": f"파일 열기 오류: {e}"}]

    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        max_row = sheet.max_row
        max_col = sheet.max_column

        for r_idx, row_cells in enumerate(sheet.iter_rows(max_row=max_row, max_col=max_col)):
            excel_row_num = r_idx + 1

            first_cell_value = row_cells[0].value
            if isinstance(first_cell_value, str) and "회사명" in first_cell_value.strip():

                for c_idx, company_header_cell in enumerate(row_cells[1:], start=1):
                    # ▼▼▼▼▼ [핵심 수정] 개별 회사 데이터를 읽는 부분을 try-except로 감쌉니다 ▼▼▼▼▼
                    try:
                        excel_col_num = company_header_cell.column
                        company_name = company_header_cell.value

                        if not isinstance(company_name, str) or not company_name.strip():
                            continue

                        cleaned_company_name = clean_text(company_name)
                        company_data = {"검색된 회사": cleaned_company_name}

                        clean_region_name = sheet_name.strip().replace('[', '').replace(']', '')
                        company_data['대표지역'] = clean_region_name

                        for item, offset in RELATIVE_OFFSETS.items():
                            target_row = excel_row_num + offset
                            if target_row <= max_row:
                                cell = sheet.cell(row=target_row, column=excel_col_num)
                                value = cell.value

                                # 데이터 처리 로직 (기존과 동일)
                                if item in ["부채비율", "유동비율"]:
                                    if isinstance(value, (int, float)):
                                        processed_value = value * 100
                                    elif isinstance(value, str):
                                        try:
                                            processed_value = float(value.replace('%', '').strip())
                                        except (ValueError, TypeError):
                                            processed_value = clean_text(value)
                                    else:
                                        processed_value = value
                                elif item == "신용평가":
                                    if isinstance(value, str):
                                        cleaned_value = value.strip()
                                        normalized_value = " ".join(cleaned_value.split())
                                        processed_value = normalized_value.replace(' ', '\n', 1)
                                    else:
                                        processed_value = value
                                else:
                                    processed_value = clean_text(value) if isinstance(value, str) else value

                                company_data[item] = processed_value if processed_value is not None else ""
                            else:
                                company_data[item] = "N/A"

                        company_statuses = {}
                        for item, offset in RELATIVE_OFFSETS.items():
                            target_row = excel_row_num + offset
                            if target_row <= max_row:
                                cell = sheet.cell(row=target_row, column=excel_col_num)
                                company_statuses[item] = get_status_from_color(cell.fill.fgColor if cell.fill else None)
                            else:
                                company_statuses[item] = "범위 초과"
                        company_data["데이터상태"] = company_statuses

                        all_companies.append(company_data)

                    except Exception as e:
                        # 오류 발생 시 로그 파일에 기록하고 다음 회사로 넘어갑니다.
                        error_msg = (f"'{sheet_name}' 시트의 {excel_row_num}행, {company_header_cell.column}열 "
                                     f"데이터 처리 중 오류 발생. 회사명: '{company_name}'. 오류: {e}")
                        print(f"[경고] {error_msg}")
                        logging.error(error_msg)
                        continue  # ★★★ 이 부분이 중요합니다 ★★★
                    # ▲▲▲▲▲ [핵심 수정] 여기까지 ▲▲▲▲▲

    if not all_companies:
        return [{"오류": "엑셀 파일에서 업체 정보를 찾을 수 없습니다."}]

    # --- 필터링 로직 (기존과 동일) ---
    filtered_results = all_companies
    if filters.get('name'):
        search_name = filters['name'].lower()
        filtered_results = [comp for comp in filtered_results if search_name in str(comp.get("검색된 회사", "")).lower()]

    if filters.get('manager'):
        search_manager = filters['manager'].lower()
        filtered_results = [comp for comp in filtered_results if search_manager in str(comp.get("비고", "")).lower()]

    if filters.get('region') and filters['region'] != "전체":
        search_region = filters['region'].strip().replace('[', '').replace(']', '')
        filtered_results = [comp for comp in filtered_results if search_region == comp.get('대표지역')]

    for key, field_name in [('sipyung', '시평'), ('perf_3y', '3년 실적'), ('perf_5y', '5년 실적')]:
        min_val, max_val = filters.get(f'min_{key}'), filters.get(f'max_{key}')
        if min_val is not None:
            filtered_results = [comp for comp in filtered_results if
                                (val := parse_amount(str(comp.get(field_name)))) is not None and val >= min_val]
        if max_val is not None:
            filtered_results = [comp for comp in filtered_results if
                                (val := parse_amount(str(comp.get(field_name)))) is not None and val <= max_val]

    if not filtered_results:
        return [{"오류": "주어진 조건에 맞는 업체를 찾을 수 없습니다."}]

    return filtered_results
