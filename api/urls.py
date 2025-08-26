from django.urls import path
# 제가 추가하라고 했던 SearchView 대신, 원래 있던 CompanySearchView를 import 합니다.

from django.conf import settings
from django.conf.urls.static import static
from .views import CompanySearchView, GetSheetNamesView, ExcelFileUploadView, CheckFileStatusView

urlpatterns = [
    # --- 이 부분을 수정해주세요 ---
    # path('search/', SearchView.as_view(), name='company-search'),  <- 이 줄 대신
    path('search/', CompanySearchView.as_view(), name='company-search'), # <- 이렇게 원래의 View를 연결

    # --- 2. 새로운 API를 위한 URL 경로를 추가합니다. ---
    path('get_regions/', GetSheetNamesView.as_view(), name='get-sheet-names'),

    path('upload/', ExcelFileUploadView.as_view(), name='excel-upload'),

    path('check_files/', CheckFileStatusView.as_view(), name='check-files'),

    # --------------------------
]

# 개발 환경에서 미디어 파일을 서빙하기 위한 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)