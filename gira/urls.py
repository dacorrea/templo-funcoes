from django.urls import path
from . import views


app_name = 'gira'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('funcoes/', views.lista_funcoes, name='lista_funcoes'),
    path('logout/', views.logout_view, name='logout'),
    path('check-user/', views.check_user_model),
    path('assumir-funcao/', views.assumir_funcao, name='assumir_funcao'),
    path('desistir-funcao/', views.desistir_funcao, name='desistir_funcao'),
    
    path('funcoes_dev/', views.lista_funcoes_dev, name='lista_funcoes_dev'),
    path('funcoes_dev/<int:gira_id>/', views.lista_funcoes_dev, name='lista_funcoes_dev_by_id'),
    path("funcoes_dev/data/<int:gira_id>/", views.get_gira_data, name="get_gira_data"),


]
