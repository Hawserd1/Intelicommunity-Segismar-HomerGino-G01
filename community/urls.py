from django.urls import path

from . import views

app_name = 'community'

urlpatterns = [
    path('communities/', views.section_list, name='section_list'),
    path('communities/<slug:slug>/', views.SectionDetailView.as_view(), name='section_detail'),
    path('communities/<slug:section_slug>/follow/', views.toggle_follow, name='toggle_follow'),
    path('communities/<slug:section_slug>/discussions/new/', views.DiscussionCreateView.as_view(), name='section_discussion_create'),
    path('discussions/', views.DiscussionListView.as_view(), name='discussion_list'),
    path('tags/<int:pk>/', views.TagDiscussionListView.as_view(), name='tag_detail'),
    path('discussions/new/', views.DiscussionCreateView.as_view(), name='discussion_create'),
    path('discussions/<int:pk>/', views.DiscussionDetailView.as_view(), name='discussion_detail'),
    path('discussions/<int:pk>/reply/', views.add_reply, name='reply_create'),
    path('discussions/<int:pk>/edit/', views.DiscussionUpdateView.as_view(), name='discussion_update'),
    path('discussions/<int:pk>/delete/', views.DiscussionDeleteView.as_view(), name='discussion_delete'),
]
