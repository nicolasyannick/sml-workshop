"""
URL configuration for utility project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from workshop import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.basic_home, name='home'),
    path('new_work_request/',views.new_work_request, name='new_work_request'),
    path('request_page/<int:work_request_id>', views.request_page, name='request_page'),
    path('status_update/', views.status_update_page, name='status_update_page'),
    path('status_update/<int:task_id>/', views.status_update, name='status_update'),
    path('calculate_workload/', views.calculate_workload, name='calculate_workload'),

]
