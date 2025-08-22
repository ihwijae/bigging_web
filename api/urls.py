from django.urls import path
from . import views

urlpatterns = [
    # 'v1/companies/search/' 주소로 요청이 오면, views.py의 CompanySearchView를 실행
    path('v1/companies/search/', views.CompanySearchView.as_view(), name='company-search'),
]