from django.urls import path
from . import views


app_name = 'gira'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('funcoes/', views.lista_funcoes, name='lista_funcoes'),
#    path('assumir/<int:pk>/', views.assumir_funcao, name='assumir_funcao'),
#    path('liberar/<int:pk>/', views.liberar_funcao, name='liberar_funcao'),
#    path('criar-gira/', views.criar_gira, name='criar_gira'),
    path('logout/', views.logout_view, name='logout'),
#    path('test-users/', test_user_list),
    path('check-user/', views.check_user_model),
 #   path('assumir/<int:pk>/', views.assumir_funcao, name='assumir_funcao'),

]
