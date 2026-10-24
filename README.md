# Template de projeto Django com DRF e PDM

Esse é um template de projeto Django com DRF, PDM e muito mais. Ele já vem com algumas configurações e pacotes pré-instalados, como o PDM, Django, Django REST Framework, PostgreSQL, SQLite, Swagger, black, isort, Render, Cloudinary, Corsheaders, Django-Extensions, Django-Filter, dotenv, dj-database-url, drf-spectacular, gunicorn, netifaces, rest-framework-simplejwt, whitenoise e passage.id

Esse template já está pronto para ser utilizado em produção, com o [Render](http://render.com) e o [PostgreSQL](https://www.postgresql.org/). Mas também pode ser utilizado em desenvolvimento, com o [PDM](https://pdm.fming.dev/) e o [SQLite](https://www.sqlite.org/index.html).

O template também já vem com alguns arquivos de configuração pré-configurados, como:

- `pyproject.toml`: Arquivo de configuração do PDM.
- `Procfile`: Arquivo de configuração do Fl0.
- `settings.py`: Arquivo de configuração do Django.
- `urls.py`: Arquivo de configuração das rotas do Django.
- `wsgi.py`: Arquivo de configuração do Gunicorn.
- `.env.exemplo`: Arquivo de exemplo de configuração das variáveis de ambiente.
- `.gitignore`: Arquivo de configuração do Git, para ignorar arquivos e diretórios.

O template também traz o usuário padrão modificado, com o login sendo feito com o `e-mail` e não com o `username`. Inclusões de campos, como `telefone`, `data de nascimento` e `foto de perfil`, podem ser feitas facilmente.

O projeto Django criado chama-se `app` e a aplicação Django criada chama-se `core`. O projeto já vem com um modelo de usuário customizado, com autenticação pelo `passage.id`. Arquivos estáticos, como fotos, podem ser armazenados no [Cloudinary](https://cloudinary.com/).

O projeto também já vem com a documentação da API, gerada automaticamente pelo Swagger, e com a formatação de código Python, feita pelo black e pelo isort.

## Instalação e Configuração

1. Certifique-se de ter o [Python](https://www.python.org/) instalado em seu sistema.

2. Crie um novo projeto a partir desse template:
- Acesse o _template_ em https://github.com/marrcandre/template_django_pdm.
- Clique no botão `Use this template` em `Create a new repository`.
- Preencha as informações solicitadas:
  - `Owner`: <seu usuário no GitHub>
  - `Repository name`: `livraria`
- Click no botão `Create repository`.

3. Abra o projeto no vscode e execute o terminal.

2. Crie um ambiente virtual usando o [PDM](https://pdm.fming.dev/):

   ```
   pdm install
   ```

3. Crie o arquivo .env, a partir do arquivo .env.exemplo, e configure as variáveis de ambiente:

   ```
   cp .env.exemplo .env
   ```

4. Execute o servidor de desenvolvimento:

   ```
   pdm run dev
   ```

5. Acesse a API em http://localhost:19003/api/

## Uso da API

A documentação completa dos endpoints da API e exemplos de uso estão disponíveis na [Documentação da API](http://localhost:19003/api/swagger/).

## Comandos Úteis

- `pdm run dev`: Executa o servidor de desenvolvimento. Antes de executar o servidor, descobre o endereço IP da máquina e atualiza o arquivo `.env` com o endereço IP.
- `pdm run migrate`: Executa as migrações do banco de dados. Antes de executar o `migrate`, executa o `makemigrations`. Depois de executar o `migrate`, executa o `graph_models`, atualizando o diagrama de classes dos modelos do projeto.
- Para mais detalhes, consulte o arquivo `pyproject.toml`, na seção `[tool.pdm.scripts]`.

## Detalhes do Projeto

Esse projeto utiliza os seguintes pacotes e tecnologias:

- [PDM](https://pdm.fming.dev/): Gerenciador de pacotes e ambiente virtual para Python.
- [Django](https://www.djangoproject.com/): Framework web de alto nível escrito em Python.
- [Django REST Framework](https://www.django-rest-framework.org/): Framework para desenvolvimento de APIs REST com Django.
- [PostgreSQL](https://www.postgresql.org/): Banco de dados relacional, utilizado no ambiente de produção.
- [SQLite](https://www.sqlite.org/index.html): Banco de dados relacional, utilizado no ambiente de desenvolvimento.
- [Swagger](https://swagger.io/): Framework para documentação de APIs REST.
- [Ruff] (http://https://docs.astral.sh/ruff/): Linter e formatador de código Python, escrito em Rust.
- [Render](http://render.com): Ferramenta de _deploy_ de aplicações _backend_.
- [Cloudinary](https://cloudinary.com/): Serviço de armazenamento de arquivos estáticos em nuvem.
- [Corsheaders](https://pypi.org/project/django-cors-headers/): Pacote para permitir que aplicações frontend acessem a API.
- [Django-Extensions](https://django-extensions.readthedocs.io/en/latest/): Pacote com extensões para o Django, como o `shell_plus`, que permite acessar o shell do Django com todos os modelos importados e o comando `graph_models`, que gera um diagrama de classes dos modelos do projeto.
- [Django-Filter](https://django-filter.readthedocs.io/en/stable/): Pacote para filtragem, ordenação e paginação de dados em APIs REST.
- [dotenv](https://pypi.org/project/python-dotenv/): Pacote para carregar variáveis de ambiente a partir de um arquivo `.env`.
- [dj-database-url](https://pypi.org/project/dj-database-url/): Pacote para configurar o banco de dados a partir de uma URL.
- [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/): Pacote para geração de documentação de APIs REST com o Swagger.
- [gunicorn](https://gunicorn.org/): Pacote para servir aplicações Django em produção.
- [netifaces](https://pypi.org/project/netifaces/): Pacote para obter o endereço IP da máquina.
- [rest-framework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/): Pacote para autenticação JWT em APIs REST.
- [whitenoise](http://whitenoise.evans.io/en/stable/): Pacote para servir arquivos estáticos em aplicações Django.
- [passage.id](https://passage.id): Pacote para autenticação de usuários.

## Licença

Este projeto está licenciado sob a [Licença GPL](https://www.gnu.org/licenses/gpl-3.0.html), uma licença de software livre.

## Recuperação de senha por e-mail

O backend implementa o fluxo de solicitação, validação e redefinição com código numérico de seis dígitos. O código é armazenado como HMAC, expira em 10 minutos, permite até cinco tentativas e é invalidado após uso. Há limite por conta de três solicitações por hora, intervalo mínimo de um minuto entre envios e throttling por IP (10 solicitações, 20 validações e 10 confirmações por hora). O limite por conta restringe o envio real de e-mails mesmo quando várias solicitações são feitas a partir do mesmo IP.

O Django mantém os contadores de throttling no cache configurado. Sem configuração explícita de `CACHES`, usa o `LocMemCache` em memória e separado por processo, inclusive em produção. Em produção com múltiplos workers ou instâncias, configure um backend compartilhado para que os limites por IP sejam consistentes. Para repetir testes, os testes automatizados limpam o cache antes de cada caso; em desenvolvimento local isolado, também é possível reiniciar o servidor ou limpar esse cache pelo shell do Django. Não exponha uma operação de limpeza de cache pela API nem a execute em produção.

Em desenvolvimento local, é possível desativar o throttling por IP e os limites de repetição por conta das rotas de recuperação configurando `DEBUG=True` e `LOCAL_DEVELOPMENT=True` no `.env` (ou no ambiente ao iniciar o processo). A exceção só se aplica a requisições cuja origem de rede e host sejam loopback (`127.0.0.1`, `localhost` ou `::1`). Sem ambas as opções ou para clientes remotos, os limites continuam ativos. Não defina `LOCAL_DEVELOPMENT=True` em produção. A validação de email/código/senha, a expiração e o limite de tentativas do código continuam ativos localmente.

O throttling por IP do DRF usa uma janela de uma hora: 10 solicitações, 20 verificações e 10 confirmações. O `Retry-After` indica o tempo restante para expirar a entrada mais antiga dessa janela, não uma duração fixa adicional. Com o `LocMemCache` padrão, as chaves são locais ao processo. Se for necessário remover somente as chaves de recuperação do loopback, execute no backend local:

```sh
pdm run python manage.py shell -c "from django.core.cache import cache; scopes=('password_reset_request','password_reset_verify','password_reset_confirm'); ips=('127.0.0.1','::1'); keys=[f'throttle_{scope}_{ip}' for scope in scopes for ip in ips]; cache.delete_many(keys)"
```

Essa operação remove apenas os seis contadores desses escopos e IPs do cache conectado àquele processo. Para outra origem, use o IP efetivo do cliente no lugar dos endereços de loopback. Não limpe todo o cache e não execute isso em produção.

Uma resposta `202` na solicitação é intencionalmente genérica e não confirma envio: ela também é usada para emails inexistentes/inativos, limites de conta e falha de entrega para evitar enumeração. Para correlacionar as etapas de uma solicitação, consulte os eventos `password_reset` no console do Django usando o mesmo `flow_id`. `stage=account result=unavailable` indica que a conta não é elegível; `stage=throttle result=blocked` indica limite de envio/reenvio; `stage=email_backend result=submission_started` indica que o envio foi iniciado; `result=accepted_by_smtp` indica aceitação pelo servidor SMTP, não entrega na caixa de entrada; e `stage=smtp_connection_or_authentication` ou `stage=smtp_submission` com `result=failed` indica falha de transporte. A ausência de `stage=request result=challenge_committed_after_backend_acceptance` após a submissão indica que o desafio não foi confirmado. Os logs não incluem email, código, senha, credenciais ou identificador da conta.

### Configuração de e-mail

Copie `.env.example` para `.env`. Em desenvolvimento, configure `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` para ver as mensagens no terminal. Para envio real, configure o backend SMTP do Django e as variáveis fornecidas pelo seu provedor:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seu-provedor.example
EMAIL_PORT=587
EMAIL_HOST_USER=usuario-smtp
EMAIL_HOST_PASSWORD=senha-ou-token-smtp
EMAIL_TIMEOUT=20
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=Livraria <nao-responda@seu-dominio.example>
```

Use TLS ou SSL conforme o provedor; não habilite ambos. Mantenha credenciais somente no ambiente de execução, nunca no repositório. Em produção, configure o domínio e o servidor da aplicação para operar por HTTPS. O envio usa `EmailMultiAlternatives`, com templates HTML e texto simples.

Para o remetente Gmail do Kando, use `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`, `EMAIL_USE_SSL=False`, `EMAIL_HOST_USER=kando.gerenciador@gmail.com` e `DEFAULT_FROM_EMAIL=kando.gerenciador@gmail.com`. `EMAIL_HOST_PASSWORD` deve ser uma senha de app do Google (com a verificação em duas etapas ativada), não a senha normal da conta. Mantenha-a somente no `.env` e nunca a registre em logs. O destinatário de cada recuperação continua sendo o endereço salvo na conta do usuário.

O fluxo usa o SMTP autenticado do Gmail, remetente igual à conta autenticada e uma mensagem multipart com alternativa HTML/texto simples. O código não controla a classificação de spam nem pode confirmar a entrega final após a aceitação SMTP. Confira a pasta Spam, marque mensagens legítimas como “Não é spam” e verifique filtros/regras e mensagens de devolução. Para `@gmail.com`, SPF, DKIM e DMARC do domínio são administrados pelo Google; não publique registros DNS para o domínio `gmail.com`. Se o remetente for migrado para um domínio próprio/Google Workspace, o administrador do domínio deve configurar SPF, ativar DKIM no Admin Console e publicar uma política DMARC alinhada ao domínio. Reputação do remetente, volume, denúncias de spam e filtros do destinatário também dependem dos serviços externos e do comportamento dos destinatários.

### Rotas

As rotas são anônimas e não alteram o login JWT existente. As respostas não informam se o e-mail está cadastrado.

1. `POST /api/auth/password-reset/request/`

   ```json
   {"email": "usuario@exemplo.com"}
   ```

   Retorna `202 Accepted` com uma mensagem genérica. Se a conta ativa existir e os limites permitirem, o código será enviado ao endereço cadastrado. Em desenvolvimento, a mensagem aparece no console; o destinatário não é aceito do cliente.

2. `POST /api/auth/password-reset/verify/`

   ```json
   {"email": "usuario@exemplo.com", "code": "012345"}
   ```

   Retorna `200` para código válido ou `400` com mensagem genérica para código inválido/expirado. Esta verificação não autoriza a redefinição por si só: a rota de confirmação valida novamente o código.

3. `POST /api/auth/password-reset/confirm/`

   ```json
   {
     "email": "usuario@exemplo.com",
     "code": "012345",
     "new_password": "NovaSenhaSegura123!",
     "confirm_password": "NovaSenhaSegura123!"
   }
   ```

   Retorna `200` após validar os validadores de senha do Django, alterar a senha e consumir o código. Senhas diferentes, senha inválida ou código inválido retornam `400`.

### Migrations, servidor e testes

```bash
pdm run python manage.py migrate
pdm run python manage.py runserver
pdm run python manage.py test core.tests
```

Os testes automatizados usam o backend de e-mail em memória e não precisam de SMTP. Para verificar a configuração efetivamente carregada sem enviar mensagem:

```bash
pdm run python manage.py diagnose_smtp --check-only
```

O projeto carrega `.env` explicitamente a partir da raiz do repositório. Variáveis já fornecidas pelo processo/ambiente têm precedência sobre `.env`; o comando sinaliza divergências sem exibir valores de usuário, remetente ou senha. Para fazer um envio SMTP real com a identidade visual do Kando, use somente um endereço que você controla ou tem autorização para testar:

```bash
pdm run python manage.py enviar_email_teste endereco-de-teste-autorizado@example.com
# ou execute sem argumento para informar o destinatário no prompt
pdm run python manage.py enviar_email_teste
```

O comando reutiliza exatamente os templates HTML/texto dos convites reais, com dados identificados como demonstração e links em `kando.example` (domínio reservado que não aponta para o backend), sem criar convites nem alterar o banco. `diagnose_smtp --recipient endereco-de-teste-autorizado@example.com` continua disponível e envia o mesmo conteúdo multipart. Ambos verificam backend, host, porta, credenciais configuradas, TLS/SSL e correspondência entre remetente e usuário autenticado; não exibem destinatário nem credenciais. A aceitação pelo SMTP significa que o servidor aceitou a mensagem para processamento; não comprova entrega na caixa de entrada. Confira spam, promoções, filtros e possíveis mensagens de devolução. Em contas Google Workspace, um administrador pode consultar o Email Log Search no Admin Console; contas pessoais Gmail não oferecem o mesmo log de rastreamento de entrega para o destinatário.

Os logs da recuperação distinguem preparação, aceitação pelo backend e falha, sem registrar endereço, código ou credenciais. Quando uma conta não está disponível, `stage=account result=unavailable` registra internamente `reason=not_found`, `reason=inactive` ou `reason=ambiguous`; a resposta pública permanece genérica. Um resultado `accepted` não é confirmação de entrega final.

### Quadros, tarefas e convites

O backend fornece uma API autenticada por JWT para quadros, tarefas e convites. O proprietário do quadro pode criar tarefas; o criador da tarefa ou o proprietário do quadro pode convidar outros usuários existentes e ativos. Tarefas podem ter responsável e participantes. Um usuário só entra na relação de participantes quando aceita explicitamente um convite pendente.

Configure `FRONTEND_BASE_URL` no ambiente de execução com a origem HTTPS real do frontend (sem caminho final), por exemplo, a URL de produção da aplicação. Essa configuração é obrigatória para enviar convites; o backend recusa URLs que não usem HTTPS. `FRONTEND_URLS` continua sendo a lista de origens CORS e não é substituída por essa configuração. O remetente usa `DEFAULT_FROM_EMAIL` (para este sistema, `kando.gerenciador@gmail.com`) e o destinatário é sempre o e-mail cadastrado do usuário convidado.

Endpoints (prefixo `/api/`; todos exigem JWT):

- `GET/POST /api/boards/`: listar quadros acessíveis ou criar um quadro (`title`, opcionalmente `description`). O proprietário é definido pelo usuário autenticado.
- `GET/POST /api/tasks/` e `GET/PATCH/PUT/DELETE /api/tasks/{id}/`: consultar/criar/gerenciar tarefas. Uma tarefa tem `board`, `title`, opcional `description`, `status` (`todo`, `in_progress`, `done`), `assignee` opcional e `due_at` opcional. `created_by` e `participants` não podem ser definidos diretamente pelo cliente.
- `POST /api/invitations/` com `{"task": 123, "email": "usuario-cadastrado@example.com"}`: cria e envia convite. Apenas criador da tarefa/dono do quadro pode convidar; destinatário precisa ser usuário ativo existente. Convites pendentes duplicados retornam `409`.
- `GET /api/invitations/pending/`: lista os convites pendentes e não expirados do usuário autenticado. `GET /api/invitations/` lista o histórico dele.
- `POST /api/invitations/{uuid}/accept/` e `POST /api/invitations/{uuid}/decline/`: responder autenticado. Apenas o destinatário vê o convite; aceite inclui o usuário nos participantes, recusa não o inclui. Respostas repetidas retornam `409`; convites expirados retornam `410`.

Os links do e-mail são páginas de confirmação no frontend: `/convites/{uuid}/aceitar` e `/convites/{uuid}/recusar`. O frontend deve mostrar diretamente a confirmação correspondente, pedir login quando necessário preservando a rota de retorno e só então chamar o endpoint POST correspondente com o JWT. Abrir ou pré-visualizar o link não altera o convite. Este repositório contém o backend; as páginas Vue precisam ser implementadas/integradas no projeto de frontend.

## Anexos do Google Drive em tarefas

O backend implementa OAuth 2.0 server-side. O usuário inicia a autorização com seu JWT, autoriza o escopo somente de leitura de metadados e retorna ao frontend após a autorização. Tokens de acesso e de atualização ficam criptografados no banco; eles nunca são enviados ao frontend nem incluídos em respostas.

### Configuração no Google Cloud

1. Crie ou selecione um projeto no [Google Cloud Console](https://console.cloud.google.com/).
2. Ative a **Google Drive API**.
3. Configure a tela de consentimento OAuth, os usuários de teste (se o app estiver em modo de teste) e a política de privacidade aplicável.
4. Crie uma credencial OAuth do tipo **Aplicativo da Web**.
5. Cadastre o URI de redirecionamento autorizado como `https://SEU-SERVICO.onrender.com/api/google-drive/callback/` (e o equivalente local, se necessário).
6. Solicite somente `https://www.googleapis.com/auth/drive.metadata.readonly`. Esse escopo permite listar e validar metadados, sem ler o conteúdo dos documentos. A verificação ou publicação do app pelo Google pode ser necessária conforme o modo de uso e a classificação do escopo.

### Variáveis de ambiente

Configure no Render e, opcionalmente, no `.env` local:

```text
GOOGLE_DRIVE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=seu-client-secret
GOOGLE_DRIVE_REDIRECT_URI=https://SEU-SERVICO.onrender.com/api/google-drive/callback/
GOOGLE_DRIVE_FRONTEND_REDIRECT_URL=https://SEU-FRONTEND/tasks
GOOGLE_DRIVE_TOKEN_ENCRYPTION_KEY=CHAVE_FERNET_GERADA_SEPARADAMENTE
```

Gere a chave Fernet fora do código e mantenha-a como segredo no Render:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Não versione esses valores. Mantenha a mesma chave de criptografia enquanto houver credenciais Google armazenadas no banco; trocá-la sem recriptografar as credenciais exige que os usuários autorizem novamente. O callback do Google e o `GOOGLE_DRIVE_REDIRECT_URI` precisam coincidir exatamente, incluindo o caminho e a barra final.

### API e fluxo do frontend

Todos os endpoints abaixo usam JWT, exceto o callback OAuth:

1. Depois que o usuário escolher criar a tarefa e ela tiver sido salva, solicite a autorização:

   ```http
   POST /api/google-drive/authorization/
   Authorization: Bearer <access-token>
   ```

   ```json
   {"authorization_url": "https://accounts.google.com/..."}
   ```

   Abra `authorization_url` no navegador. O Google retorna ao backend em `/api/google-drive/callback/`; o backend valida o estado OAuth de uso único, armazena os tokens criptografados e redireciona o navegador para `GOOGLE_DRIVE_FRONTEND_REDIRECT_URL?google_drive=connected`. Cancelamento e falhas retornam `google_drive=denied`, `authorization_error` ou `configuration_error`. Nenhum token OAuth aparece na URL de retorno.

2. Consulte os arquivos acessíveis à conta conectada:

   ```http
   GET /api/google-drive/files/?page_token=<opcional>
   Authorization: Bearer <access-token>
   ```

   ```json
   {
     "files": [
       {
         "id": "google-file-id",
         "name": "Planejamento.pdf",
         "mime_type": "application/pdf",
         "size": 12345,
         "web_view_link": "https://drive.google.com/file/d/google-file-id/view"
       }
     ],
     "next_page_token": null
   }
   ```

3. Envie os IDs selecionados para a task já criada:

   ```http
   POST /api/tasks/42/drive-attachments/
   Authorization: Bearer <access-token>
   Content-Type: application/json
   ```

   ```json
   {"file_ids": ["google-file-id"]}
   ```

   A resposta `200` contém os anexos associados. O backend confirma cada ID usando a API do Google Drive com a conta autorizada antes de persistir. A mesma requisição pode ser repetida sem duplicar task ou anexos. Uma autorização ausente/expirada retorna `401`; arquivo inexistente ou inacessível, `400`; falha do provedor, `502`.

4. Consulte ou remova associações:

   ```http
   GET /api/tasks/42/drive-attachments/
   DELETE /api/tasks/42/drive-attachments/7/
   ```

   Somente o criador da task ou o proprietário do board pode associar/remover anexos, conforme as permissões existentes para escrita em tasks. Participantes podem consultar os anexos, de acordo com a permissão de leitura. A remoção exclui somente a associação no backend; não apaga o arquivo do Drive.

O frontend deve manter a task criada enquanto abre a etapa de seleção, usar a autorização se ainda não houver conta conectada, carregar os arquivos paginados, permitir seleção múltipla e enviar os IDs à rota da task existente. Como a autorização redireciona o navegador, preserve o ID da task em estado local seguro (por exemplo, `sessionStorage`) e retome a seleção quando o frontend receber `google_drive=connected`. Em caso de falha de associação, repetir o POST não cria uma segunda task nem duplica a associação.
