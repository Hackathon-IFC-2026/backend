# Backend integrado do Kando

Esta pasta (src/backend/backend) contém o código integrado e tem seu próprio repositório Git. O Django não depende da pasta backend-integration para executar.

## Alterações incorporadas

- Projetos, participantes e tarefas nos endpoints /api/projetos/, /api/participantes-projeto/ e /api/tarefas/.
- Permissões específicas por projeto, múltiplos administradores e proteção do último administrador.
- Comentários, checklists, materiais, notificações e alertas de prazo.
- Perfil, nascimento, upload/remoção de foto e troca de senha com invalidação dos tokens antigos.
- Migrações 0013 até 0017, adicionadas sem substituir as migrações antigas.
- Dependências atualizadas em pyproject.toml, pdm.lock e requirements.txt.
- Registro dos modelos e rotas, autenticação JWT e CORS.

Os modelos e tabelas legados Board/Task continuam disponíveis. Nenhum ID desses modelos é misturado com Projeto/Tarefa.

## Executar

Dentro desta pasta:

    pdm install
    pdm run python manage.py migrate
    pdm run python manage.py runserver

O SQLite local já recebeu as migrações até 0017 nesta integração. O ambiente publicado ainda precisa receber o código e executar suas próprias migrações. Não usar app.test_settings fora dos testes.

## Verificar

    pdm run python manage.py check
    pdm run python manage.py makemigrations --check --dry-run
    pdm run python manage.py test core.tests --settings=app.test_settings --noinput

## Revisar e preparar seu commit

Os conflitos anteriores em .env.example, .pdm-python e db.sqlite3 foram resolvidos. O arquivo do banco em uso foi preservado e atualizado por migrações. As cinco contas e os registros das nove tabelas anteriores foram comparados com o backup e preservados.

Há uma cópia anterior do código, do banco e dos estágios de conflito em:

    C:/Users/thaynabecker/frontend/.backend-backups/20261024-035259/

A pasta de backup é local e está ignorada pelo Git do frontend.

Confira os arquivos:

    git status
    git diff
    git diff --cached

Para preparar apenas o código e a documentação:

    git add app core pyproject.toml pdm.lock requirements.txt .env.example INTEGRACAO_KANDO.md

Não adicionar .env, db.sqlite3, .pdm-python, arquivos de mídia ou __pypackages__ ao commit. O banco e o caminho do interpretador já eram rastreados pelo repositório; devem ser revisados separadamente como arquivos locais.

Nenhum commit ou push foi realizado nesta integração. A operação de merge que já existia no repositório permanece aguardando o commit de revisão.

## Publicação

Publicar o código revisado no repositório do backend. Na hospedagem, executar python manage.py migrate com as variáveis e o banco de produção. O build.sh já inclui esse comando, caso seja o script utilizado pela hospedagem.

Para fotos em produção, usar CLOUDINARY_URL ou armazenamento persistente com MEDIA_URL apropriado. Para alertas mesmo sem usuários conectados, agendar python manage.py notificar_prazos a cada cinco minutos.
