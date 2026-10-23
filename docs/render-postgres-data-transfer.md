# PostgreSQL no Render e transferência dos dados locais

## Configuração do serviço

O Django usa `DATABASE_URL` por `dj_database_url`. Em desenvolvimento, o valor
padrão continua sendo `sqlite:///db.sqlite3`. Com `DEBUG=False`, o settings
exige que `DATABASE_URL` esteja definido e que a URL aponte para PostgreSQL;
isso evita que uma configuração de produção incompleta crie silenciosamente um
banco SQLite efêmero.

No painel Render:

1. Abra o Dashboard e escolha **New + → PostgreSQL**. Defina nome e região
   próximos ao serviço web, escolha um plano adequado e crie o banco. Confirme
   no painel que ele está disponível e que há um backup/snapshot antes de
   qualquer alteração.
2. Abra o serviço web `backend-mknu` e vincule-o ao PostgreSQL recém-criado (ou
   configure `DATABASE_URL` como referência à Internal Database URL do banco).
   Não use a URL pública do backend como URL do banco.
3. Nas variáveis de ambiente do serviço, configure `DEBUG=False`, uma `SECRET_KEY`
   própria como secret, `ALLOWED_HOSTS=backend-mknu.onrender.com` e `DATABASE_URL`
   usando a URL interna/variável vinculada ao PostgreSQL do Render. Não copie a
   URL real para este repositório. Se o serviço também receber tráfego por outro
   domínio próprio, inclua esse host na lista separada por vírgulas.
4. O projeto já declara `psycopg2-binary` no `pyproject.toml`, `pdm.lock` e
   `requirements.txt`.
5. Configure o build command como `./build.sh` e o start command como
   `gunicorn app.wsgi:application --bind 0.0.0.0:$PORT --log-file -` (também
   presente no `Procfile`). O build
   instala dependências e coleta estáticos, mas não executa migrations.
6. Configure o Pre-Deploy Command do serviço para
   `python manage.py migrate`. Ele deve executar somente depois de revisar o
   código/migrations e antes de servir a nova versão. Se o plano do Render não
   oferecer Pre-Deploy Command, use o Shell do serviço e execute
   `python manage.py migrate` de forma explícita, depois do backup.

Migrations criam/altera(m) estrutura; não transferem registros. `0012` cria as
tabelas de quadros, tarefas e convites e deve ser aplicada pelo processo acima.
Não use `--fake`.

## Preparar uma exportação local

Pare temporariamente processos que gravem no SQLite durante a exportação.
O comando recusa conexões que não sejam SQLite, cria um backup consistente do
arquivo e exporta os modelos `core` e grupos do Django. Desafios de recuperação
de senha e sessões não são transferidos. O JSON inclui dados pessoais e hashes
de senha; guarde os dois arquivos de forma privada.

```bash
cd /caminho/para/backend
umask 077
transfer_dir="$HOME/kando-transfer-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$transfer_dir"
pdm run python manage.py export_local_data --directory "$transfer_dir"
```

O comando recusa sobrescrever os arquivos de saída, define permissão `0600` e
informa contagens por modelo. O backup SQLite e o fixture são independentes;
preserve o backup até concluir a validação.

## Preparar e revisar o destino

Crie um snapshot/backup do PostgreSQL no painel do Render antes de migrations ou
importação. Use a URL externa do PostgreSQL somente no terminal local para a
conexão de importação; não a grave em arquivos nem a coloque na linha do
comando. `read -s` evita que a URL seja ecoada:

```bash
read -r -s -p "External Database URL do PostgreSQL Render: " DATABASE_URL
printf '\n'
export DATABASE_URL
```

Confirme o alvo e a situação das migrations sem alterar registros:

```bash
pdm run python manage.py shell -c \
"from django.db import connection; print('DB vendor:', connection.vendor)"
pdm run python manage.py showmigrations --plan
pdm run python manage.py import_local_data --check-only
```

O vendor precisa ser `postgresql`; o comando de diagnóstico lista as contagens
de dados sem importar. Se a configuração indicar SQLite, URL incorreta ou
migrations pendentes, pare. Aplique migrations apenas depois do snapshot:

```bash
pdm run python manage.py migrate
pdm run python manage.py import_local_data --check-only
```

`--check-only` não modifica registros. Antes de prosseguir, confirme no painel
que o snapshot está concluído e revise as contagens. A importação só continua
quando todos os modelos `core` e grupos do Django no destino estão vazios.
Se houver dados, o comando aborta; não há modo de merge automático.

## Importar e verificar

Com o alvo PostgreSQL confirmado, snapshot disponível e destino vazio:

```bash
pdm run python manage.py import_local_data \
  "$transfer_dir/kando-local.json" \
  --confirm-empty-destination \
  --confirm-remote-backup
pdm run python manage.py import_local_data --check-only
```

O comando exige PostgreSQL e migrations aplicadas, valida que o fixture contém
somente modelos permitidos, bloqueia as tabelas de dados durante a operação,
verifica novamente que estão vazias e carrega tudo em uma transação. Uma falha
ou colisão reverte a transação. Os IDs exportados são mantidos; o `loaddata` do
Django reseta as sequências compatíveis do PostgreSQL. Depois, a contagem por
modelo deve corresponder à exportação; o comando também valida essas contagens e
falha/rollback se divergirem.

`--confirm-remote-backup` confirma que você criou o snapshot no painel; o
comando não cria nem valida esse snapshot. `--confirm-empty-destination`
também é obrigatório e não ignora a checagem real das tabelas.

Não importe um fixture integral em uma base já povoada. Nesse caso, faça um
plano de merge específico com backup e mapeamento explícito de usuários e
chaves estrangeiras. Arquivos de mídia não estão no banco relacional e precisam
ser transferidos separadamente se houver algum.

Se o fixture trouxe um superusuário local adequado, ele continuará sendo
superusuário com o hash de senha preservado. Caso contrário, crie uma conta no
ambiente que aponta para PostgreSQL usando `python manage.py createsuperuser`;
o comando solicita os dados interativamente. Nunca coloque a senha no código
ou em argumentos salvos.

Após verificar o login e os dados, remova o fixture quando a política de
retenção permitir. Limpe a variável do terminal ao finalizar:

```bash
unset DATABASE_URL
```
