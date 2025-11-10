# gira/views_schema.py
from django.http import JsonResponse, HttpResponseForbidden
from django.apps import apps
from django.conf import settings

def schema_view(request):
    # proteção simples por token GET ?token=SEUTOKEN ou permitir somente DEBUG/ADMIN
    secret = getattr(settings, 'SCHEMA_VIEW_TOKEN', None)
    token = request.GET.get('token')
    if secret and token != secret:
        return HttpResponseForbidden('Token inválido')

    data = {}
    for model in apps.get_models():
        model_name = f"{model._meta.app_label}.{model.__name__}"
        fields = []
        for field in model._meta.get_fields():
            # ignorar relações automáticas reversas muito verbosas, manter FK/Field úteis
            try:
                fdict = {
                    'name': field.name,
                    'type': field.get_internal_type(),
                    'null': getattr(field, 'null', None),
                }
                # adicionar FK info se existir
                if getattr(field, 'remote_field', None) and getattr(field.remote_field, 'model', None):
                    fdict['fk_to'] = f"{field.remote_field.model._meta.app_label}.{field.remote_field.model.__name__}"
                fields.append(fdict)
            except Exception:
                # segurança: ignorar campos inesperados
                pass
        data[model_name] = fields
    return JsonResponse(data, json_dumps_params={'indent': 2}, safe=True)
