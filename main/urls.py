from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('disciplines/', views.get_disciplines, name='get_disciplines'),
    path('tournaments/', views.get_tournaments, name='get_tournaments'),
    path('tournaments/create/', views.create_tournament, name='create_tournament'),
    path('teams/', views.get_teams, name='get_teams'),
    path('teams/create/', views.create_team, name='create_team'),
    path('participants/', views.get_participants, name='get_participants'),
    path('participants/create/', views.create_participant, name='create_participant'),
    path('matches/', views.get_matches, name='get_matches'),
    path('matches/generate/', views.generate_matches, name='generate_matches'),
    path('matches/<int:match_id>/update/', views.update_match, name='update_match'),    
    path('logout/', views.logout, name='logout'),
]