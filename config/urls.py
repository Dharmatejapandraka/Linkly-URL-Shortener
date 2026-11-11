
from django.contrib import admin
from django.urls import path
from shortener import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('', views.home, name='home'),
    path('api/shorten/', views.shorten_url, name='shorten_url'),
    path('qr/<str:short_code>/', views.generate_qr, name='generate_qr'),
    path('<str:short_code>/', views.redirect_url, name='redirect_url'),
    path(
    'dashboard/delete/<int:link_id>/',
    views.delete_short_url,
    name='delete_short_url'
),
]
