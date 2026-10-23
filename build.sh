#!/usr/bin/env bash
# Sai do script se houver algum erro
set -o errexit

# Atualiza o pip
pip install --upgrade pip

# Instala as dependências
pip install -r requirements.txt

# Coleta os arquivos estáticos
python manage.py collectstatic --no-input

# Falha em vez de aplicar migrations no SQLite padrão ou num banco implícito.
: "${DATABASE_URL:?Configure DATABASE_URL do PostgreSQL no serviço Render}"
case "${DEBUG:-}" in
    false|False|FALSE) ;;
    *)
        echo "Configure DEBUG=False no Render antes de aplicar migrations." >&2
        exit 1
        ;;
esac

# Aplica migrations pendentes no PostgreSQL selecionado por DATABASE_URL.
python manage.py migrate --noinput
