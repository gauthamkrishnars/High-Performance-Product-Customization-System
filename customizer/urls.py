from django.urls import path
from . import views

app_name = 'customizer'

urlpatterns = [
    # Main Studio Interface
    path('', views.StudioView.as_view(), name='studio'),
    path('catalog/', views.CatalogView.as_view(), name='catalog'),
    path('jobs/<uuid:job_id>/', views.JobDetailView.as_view(), name='job_detail'),
    
    # API endpoints
    path('api/upload-design/', views.upload_design_api, name='api_upload_design'),
    path('api/select-preset/', views.select_preset_api, name='api_select_preset'),
    path('api/render-mockup/', views.render_mockup_api, name='api_render_mockup'),
    path('api/jobs/<uuid:job_id>/status/', views.job_status_api, name='api_job_status'),
    path('api/products/<int:product_id>/angles/', views.product_angles_api, name='api_product_angles'),
]
