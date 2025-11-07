from django.contrib import admin
from .models import UserProfile, Medium, CambonePool, Gira, Funcao, Historico
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('celular', 'nome', 'is_staff')
    search_fields = ('celular', 'nome')
    ordering = ('celular',)
    fieldsets = (
        (None, {'fields': ('celular', 'password')}),
        ('Informações pessoais', {'fields': ('nome', 'email')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('celular', 'password1', 'password2'),
        }),
    )


admin.site.register(UserProfile)
admin.site.register(Medium)
admin.site.register(CambonePool)
admin.site.register(Gira)
admin.site.register(Funcao)
admin.site.register(Historico)
