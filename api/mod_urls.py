from django.urls import path

from api import mod_views as views

# Todas las rutas bajo /api/mod/ requieren JWT de moderador.
# fusionar/ debe ir antes de <str:pk>/ para evitar que Django lo capture como pk.
urlpatterns = [
    path('cola/', views.ColaView.as_view(), name='mod-cola'),

    path('centros/', views.ModCentroListView.as_view(), name='mod-centro-list'),
    path('centros/fusionar/', views.ModFusionarView.as_view(), name='mod-fusionar'),
    path('centros/<str:pk>/', views.ModCentroDetailView.as_view(), name='mod-centro-detail'),
    path('centros/<str:pk>/verificar/', views.ModVerificarView.as_view(), name='mod-verificar'),
    path('centros/<str:pk>/ocultar/', views.ModOcultarView.as_view(), name='mod-ocultar'),
    path('centros/<str:pk>/reemitir-codigo/', views.ModReemitirCodigoView.as_view(), name='mod-reemitir-codigo'),

    path('reportes/', views.ModReporteListView.as_view(), name='mod-reporte-list'),
    path('reportes/<str:pk>/resolver/', views.ModReporteResolverView.as_view(), name='mod-reporte-resolver'),

    path('catalogo/', views.ModCatalogoListView.as_view(), name='mod-catalogo-list'),
    path('catalogo/<str:pk>/', views.ModCatalogoDetailView.as_view(), name='mod-catalogo-detail'),

    path('moderadores/', views.ModeradorListView.as_view(), name='mod-moderador-list'),
    path('moderadores/<str:pk>/', views.ModeradorDetailView.as_view(), name='mod-moderador-detail'),

    path('metricas/', views.MetricasView.as_view(), name='mod-metricas'),

    path('contactos-emergencia/', views.ModContactoEmergenciaListView.as_view(), name='mod-contacto-list'),
    path('contactos-emergencia/<str:pk>/', views.ModContactoEmergenciaDetailView.as_view(), name='mod-contacto-detail'),
]
