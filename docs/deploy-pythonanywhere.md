# Deploy e recuperação do prova-naped

Este procedimento é específico de `rodrigoniskier.pythonanywhere.com` e do
repositório `rodrigoniskier/prova-naped`. Código integrado não comprova deploy.

## Antes de executar

1. Confirme pelo painel autenticado a aplicação, checkout realmente importado
   pelo WSGI, branch `main`, virtualenv, versão de Python, banco e mapas de mídia/estáticos.
   A configuração efetiva de produção não pode ser inferida apenas do GitHub.
2. Inspecione `git status --short`, `git remote` e o SHA atual sem exibir credenciais.
   Preserve alterações locais. Nunca use `reset --hard` ou `clean`.
3. Confirme o SHA aprovado após CI e merge. Se `main` avançar, revise a diferença.
4. Confirme que `SECRET_KEY` de produção tem valor privado e adequado e que o
   ambiente do console reproduz as variáveis/configurações do WSGI. Não copie
   segredos para chat, Git ou logs. Não altere a chave em uso como parte deste deploy.
5. Valide o estado das migrações e eventuais customizações locais. Como o
   repositório legado rastreia `db.sqlite3`, modificações no banco de produção
   podem tornar o checkout sujo: o script interrompe antes de modificar esse estado.

## Script reutilizável

Execute `scripts/deploy_pythonanywhere.py` com o Python do virtualenv confirmado,
no próprio PythonAnywhere. Os argumentos abaixo são marcadores e devem ser
substituídos por caminhos **observados**, nunca por suposições:

```text
<PYTHON_DO_VIRTUALENV> scripts/deploy_pythonanywhere.py \
  --checkout <CHECKOUT_CONFIRMADO> \
  --approved-sha <SHA_APROVADO_DE_40_CARACTERES> \
  --wsgi <WSGI_CONFIRMADO> \
  --backup-dir /home/rodrigoniskier/deploy-backups
```

O script exige a conta correta, origin esperado, `main`, checkout limpo e WSGI
apontando para o checkout. Se a API estiver autenticada por `API_TOKEN` ou
`PYTHONANYWHERE_API_TOKEN` **já presentes no servidor**, valida a configuração
pela API oficial e usa apenas o endpoint de reload desta aplicação. Nunca imprime o token.
Não cria consoles, chaves nem endpoints remotos.

Sem API disponível, use `--reload-via-ui` depois de conferir o virtualenv no
painel. Nesse modo o script apenas prepara código/banco/estáticos e termina
**com reload pendente**; é obrigatório realizar e comprovar o reload na UI.

O fluxo efetivo:

- lock exclusivo por aplicação; checks iniciais e plano das migrações;
- fetch e comparação do SHA aprovado com `origin/main`;
- backup consistente pela API de backup do SQLite, abertura do backup,
  `integrity_check`, `foreign_key_check` e validação da tabela de migrações;
- recibo fora do repositório, com SHA anterior, checksum SHA-256, backup,
  intérprete e versões dos pacotes anteriores; arquivos de backup modo 0600;
- `git pull --ff-only origin <SHA aprovado>`: fixa o conteúdo revisado mesmo se
  a branch remota avançar entre o fetch e o pull;
- instalação das dependências fixadas somente quando o arquivo mudou;
- `pip check`, checks Django/deploy, plano e aplicação das migrações,
  confirmação de ausência de migrações pendentes e `collectstatic`;
- reload pela API (se selecionado), sem repetição automática de POST ambíguo.

Falhas lançam exceção/código não zero e interrompem as etapas seguintes.
O script não fornece rollback destrutivo automático. Seus testes verificam
backup/restauração estrutural e bloqueios de conta/SHA, mas não simulam um
servidor de produção nem comprovam o fluxo remoto completo.

A migração é aditiva e não altera os registros pedagógicos anteriores. Após o
deploy, o formulário estará vazio até que um administrador associe componentes
a um semestre real e ative esse semestre. Não classifique o acervo por conta própria.

## Pós-deploy obrigatório

Registre o resultado do pull e o HEAD, o caminho/checksum do backup, as migrações
aplicadas e a resposta do reload. Consulte o error log correspondente a esta
aplicação e diferencie exceções anteriores de eventos posteriores ao reload.

Verifique HTTPS, login, Admin, menu, listagem de semestres ativos, doador,
receptores permitidos, paginação, seleção e estáticos carregados. Não conclua
apenas por HTTP 200. Não importe nem exclua questões acadêmicas reais para testar.
O teste de clonagem usa os dados sintéticos segregados na suíte local/CI.

## Recuperação

Mantenha o SHA anterior e o recibo/backup fora do checkout. Em falha de código,
pare e examine logs antes de escolher a recuperação. Preserve qualquer alteração
local e confirme se novos registros legítimos foram criados desde o backup.

Com checkout limpo, um `git switch --detach <SHA_ANTERIOR>` é uma recuperação de
código controlada, sem apagar arquivos não rastreados. Reestabeleça dependências
conforme o inventário anterior, confira o WSGI, execute checks e recarregue somente
esta aplicação. Registre que o checkout ficou em detached HEAD para posterior
retorno controlado à branch. Se o Git identificar conflito com o banco rastreado
ou outros arquivos, pare e preserve esse estado; não force o checkout.

As tabelas aditivas podem permanecer para a versão anterior ignorar, sem apagar
recibos nem questões novas. Não reverta a migração automaticamente: isso apagaria
as tabelas de semestres e auditoria. Restaurar o banco só é admissível após avaliar
as transações posteriores ao backup e uma estratégia de preservação/conciliação.
Abertura e integridade do snapshot comprovam recuperabilidade estrutural; não
comprovam ausência de perdas se ele substituir um banco mais recente.

API oficial consultada: https://help.pythonanywhere.com/pages/API/
