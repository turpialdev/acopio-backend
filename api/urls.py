from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('health/', views.health, name='health'),

    path('auth/codigo/', views.AuthCodigoView.as_view(), name='auth-codigo'),
    path('auth/moderador/', views.AuthModeradorView.as_view(), name='auth-moderador'),

    path('centros/', views.CentroListView.as_view(), name='centro-list'),
    path('centros/<str:pk>/reportar/', views.CentroReportarView.as_view(), name='centro-reportar'),
    path('centros/<str:pk>/sugerencias/', views.SugerenciasView.as_view(), name='centro-sugerencias'),
    path('centros/<str:pk>/', views.CentroDetailView.as_view(), name='centro-detail'),

    path('contactos-emergencia/', views.ContactoEmergenciaListView.as_view(), name='contacto-emergencia-list'),

    path('catalogo/', views.CategoriaListView.as_view(), name='categoria-list'),
    path('catalogo/<str:pk>/', views.CategoriaDetailView.as_view(), name='categoria-detail'),

    path('necesidades/', views.NecesidadListView.as_view(), name='necesidad-list'),
    path('necesidades/<str:pk>/', views.NecesidadDetailView.as_view(), name='necesidad-detail'),

    path('movimientos/', views.MovimientoListView.as_view(), name='movimiento-list'),
    path('movimientos/<str:pk>/', views.MovimientoDetailView.as_view(), name='movimiento-detail'),
]
