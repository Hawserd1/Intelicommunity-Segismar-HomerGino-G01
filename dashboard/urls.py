from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('member/', views.member_dashboard, name='member'),
    path('moderator/', views.moderator_dashboard, name='moderator'),
    path('administrator/', views.administrator_dashboard, name='administrator'),
    path('coming-soon/<slug:feature>/', views.coming_soon, name='coming_soon'),
    path('administrator/users/', views.user_management, name='user_management'),
    path('moderator/reports/', views.reported_content, name='reported_content'),
    path('moderator/reports/<int:pk>/review/', views.review_report, name='review_report'),
    path('moderator/activity-reports/', views.activity_reports, name='activity_reports'),
]
