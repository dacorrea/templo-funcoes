#!/usr/bin/env bash
# render_build.sh

echo "🚀 Iniciando build no Render..."

#set -o errexit  # interrompe se algum comando falhar

echo "📦 Instalando dependências..."
#pip install -r requirements.txt

echo "🧱 Aplicando migrações..."
# python manage.py migrate --noinput

echo "🧱 Rodando migrações..."
#python manage.py makemigrations gira --noinput || echo "⚠️ Nenhuma migração necessária"
#python manage.py migrate --noinput

echo "✅ Build concluído com sucesso!"
