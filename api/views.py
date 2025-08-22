from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os

# --- [수정] Swagger UI에 파라미터 정보를 알려주기 위해 import 추가 ---
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
# -------------------------------------------------------------

# 기존 로직 파일을 import 합니다.
from . import search_logic


class CompanySearchView(APIView):
    """
    업체명으로 협력업체 엑셀 파일에서 회사를 검색하는 API
    """

    # --- [수정] @swagger_auto_schema 데코레이터를 추가하여 파라미터 정보를 명시 ---
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'name',  # 파라미터 이름
                openapi.IN_QUERY,  # 파라미터 위치 (URL 쿼리)
                description="검색할 회사명의 일부를 입력하세요.",  # 설명
                type=openapi.TYPE_STRING  # 파라미터 타입
            )
        ]
    )
    # --------------------------------------------------------------------
    def get(self, request, *args, **kwargs):
        # 1. URL 쿼리 파라미터에서 'name' 값을 가져옵니다. (예: ?name=태건)
        company_name = request.query_params.get('name', None)

        if not company_name:
            return Response(
                {"error": "검색할 업체명('name' 파라미터)이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. settings.py에 설정된 엑셀 데이터 폴더 경로를 가져옵니다.
        excel_dir = settings.EXCEL_DATA_DIR

        # ★★★ 중요 ★★★
        # 우선 '전기.xlsx' 파일 하나만 대상으로 검색하도록 고정합니다.
        # 나중에는 어떤 파일을 검색할지 파라미터로 받을 수 있습니다.
        excel_file_path = os.path.join(excel_dir, '전기.xlsx')

        if not os.path.exists(excel_file_path):
            return Response(
                {"error": f"'{excel_file_path}' 파일을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 기존에 만들어둔 search_logic 함수를 그대로 사용합니다.
        try:
            filters = {'name': company_name}
            results = search_logic.find_and_filter_companies(excel_file_path, filters)

            # 4. 결과를 JSON 형태로 응답합니다.
            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"검색 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
