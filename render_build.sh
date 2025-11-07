#!/usr/bin/env bash
# render_build.sh

echo "📦 Instalando dependências..."
pip install -r requirements.txt

echo "📦 Rodando migrações do Django..."
python manage.py makemigrations --noinput || true
python manage.py migrate --noinput || true

echo "✅ Migrações concluídas."

