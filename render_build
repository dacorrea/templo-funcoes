#!/usr/bin/env bash
# Este script é executado automaticamente no deploy do Render

echo "📦 Rodando migrações do Django..."
python manage.py makemigrations gira --noinput
python manage.py migrate --noinput

echo "✅ Migrações concluídas."
