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

O backend implementa o fluxo de solicitação, validação e redefinição com código numérico de seis dígitos. O código é armazenado como HMAC, expira em 10 minutos, permite até cinco tentativas e é invalidado após uso. Há limite por conta de três solicitações por hora, intervalo mínimo de um minuto entre envios e throttling por IP (5 solicitações, 20 validações e 10 confirmações por hora).

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

Para Gmail, use `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True` e `EMAIL_USE_SSL=False`. `EMAIL_HOST_PASSWORD` deve ser uma senha de app do Google (com a verificação em duas etapas ativada), não a senha normal da conta nem o texto ilustrativo do `.env.example`. O usuário e o remetente (`EMAIL_HOST_USER` e `DEFAULT_FROM_EMAIL`) devem pertencer à conta autorizada a enviar.

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

Os testes usam o backend de e-mail em memória e não precisam de SMTP. Para validar o recebimento real, configure as credenciais do seu provedor no ambiente, selecione o backend SMTP, inicie a aplicação e solicite a recuperação para um endereço cadastrado; confirme a chegada na caixa de entrada e também na pasta de spam. A aplicação reporta falhas de entrega no log do servidor sem expor detalhes SMTP ao cliente.
