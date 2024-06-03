# torrents/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('top/', views.default_top, name='default_top'),
    path('top48h/', views.default_top, name='default_top'),
    path('top/<int:cat>/', views.top_torrents, name='top_torrents'),
    path('top48h/<int:cat>/', views.top48h_torrents, name='top48h_torrents'),
    path('recent/', views.recent_torrents, name='recent_torrents'),
    path('recent/<int:page>/', views.recent_torrents, name='recent_torrents'),
    path('api-search/', views.api_search, name='api_search'),
    path('search/', views.default_search, name='default_search'),
    path('search/<str:term>/', views.search_torrents, name='search_torrents'),
    path('search/<str:term>/<int:page>/', views.search_torrents, name='search_torrents'),
]
