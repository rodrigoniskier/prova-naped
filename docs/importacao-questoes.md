# Importação de Questões entre Componentes

## Uso e configuração

Após migração e reload, acesse `/admin/questoes/importacaoquestao/importar/`
pelo menu próprio no Jazzmin. O histórico fica em
`/admin/questoes/importacaoquestao/`.

1. Cadastre em **Semestres letivos** o semestre real, seus componentes e a situação ativa.
   A migração não presume que o acervo existente pertença a um semestre específico.
2. Escolha o semestre e carregue os componentes. Selecione o doador e carregue as questões.
3. Marque questões, filtre por texto/status e use a paginação. A seleção permanece
   ao navegar pelos botões do formulário. É possível selecionar todas do filtro
   (até 500), limpar a seleção inteira ou atuar apenas na página atual (25 itens).
4. Escolha um receptor do mesmo semestre, diferente do doador.
5. Revise o resumo e confirme **Importar questões**. Cópias já registradas para
   aquele receptor são ignoradas. Nenhuma questão original é removida ou alterada.

Superusuários têm acesso. Para outros usuários, exija `is_active`, `is_staff` e
as permissões `questoes.importar_questoes`, `questoes.view_questao` e
`questoes.add_questao`. Configure semestres com um administrador que possua as
permissões de cadastro correspondentes. A interface não concede permissões automaticamente.

## Arquitetura observada e decisões

O projeto possuía apenas `Periodo` (período **do curso**, como "1º Período"),
`ComponenteCurricular`, `Questao` e `Alternativa`. Não havia semestre letivo,
autor, data de cadastro, assunto, tipo explícito de questão, anexos além da imagem,
histórico de aprovação nem vínculos persistidos com provas ou tentativas.
Não são apresentados nem inventados campos ausentes.

A migração `0002_semestreletivo_importacaoquestao` é aditiva:

- `SemestreLetivo`: nome, ativo (padrão falso) e componentes M2M. Um componente
  pode participar de diversos semestres. O banco de questões continua pertencendo
  ao componente; não há atribuição retroativa de semestre às questões antigas.
- `ImportacaoQuestao`: recibo com origem, ID original permanente, nome do doador
  no momento da importação, cópia, receptor, semestre, responsável e data.
  Restrição única `(origem_identificador, receptor)` protege contra reenvios e
  concorrência. Enunciados iguais não estabelecem identidade.

As FKs de origem/cópia usam `SET_NULL`, permitindo excluir qualquer questão sem
invalidar a outra. Receptor/semestre/responsável usam `PROTECT` para preservar o
recibo. Excluir a cópia não libera reimportação da mesma origem para aquele receptor;
o recibo permanece e o resultado é "ignorada". Importações anteriores sem recibo
não têm origem inferida e não são deduplicadas por enunciado.

`importacao.py` concentra a clonagem. A transação durável exige que o serviço seja
chamado fora de outra transação de aplicação; `ATOMIC_REQUESTS` não está habilitado.
O primeiro comando é uma escrita de bloqueio no semestre ativo: serializa escritores
no SQLite, e o bloqueio de linha funciona em bancos com `SELECT FOR UPDATE`.
Componentes, vínculos, questões e alternativas são revalidados dentro da transação.
A restrição única é uma segunda defesa persistente.

Cada imagem é copiada por streaming para um caminho UUID independente. Falhas
removem os novos arquivos e revertem todo o lote no banco. Uma interrupção abrupta
externa (por exemplo, encerramento do processo pelo sistema durante gravação) pode
exigir investigação de arquivos órfãos; banco e filesystem não têm commit distribuído.
Nenhuma rotina apaga automaticamente mídias de questões excluídas. Essa é a política
preexistente do Django neste projeto, que evita apagar arquivos ainda referenciados.

Todos os dados pedagógicos existentes são copiados: texto-base, enunciado,
justificativa, imagem e alternativas na sequência de suas PKs, incluindo gabarito.
Não há campo de ordenação explícito no modelo original. Toda cópia começa `PENDENTE`.
O operador é registrado como responsável pela importação, sem ser declarado autor
ou aprovador. A consulta das alternativas usa prefetch; páginas têm 25 questões,
e cada operação limita-se a 500.

A view é protegida pelo Admin, permissões e CSRF. O estado da seleção é assinado,
expira em uma hora e usa chave aleatória mantida na sessão do operador. IDs,
componentes, semestre ativo, quantidade e receptor são sempre validados novamente.
A confirmação vincula a seleção ao receptor. Os textos são escapados no template.
O JavaScript apenas seleciona checkboxes e atualiza o contador; formulários e
paginação funcionam sem ele.

Django permanece na série 5.2 LTS, com patch 5.2.18. Jazzmin 3.0.1 foi identificado
pelo hash idêntico de `staticfiles/jazzmin/css/main.css` e preserva os estilos existentes.
As dependências estão fixadas, incluindo Pillow, necessário ao `ImageField`.
`LOGIN_REDIRECT_URL='admin:index'` corrige a navegação após login direto no Admin.

## Verificação reproduzível

Use ambiente virtual descartável. Os testes usam banco e mídia temporários,
sem reutilizar `db.sqlite3` do checkout.

```bash
python -m pip install -r requirements.txt
python manage.py check --settings=gerador_provas.test_settings
python manage.py makemigrations --check --dry-run --settings=gerador_provas.test_settings
python manage.py test --settings=gerador_provas.test_settings --verbosity=2
python -m unittest discover -s scripts -p 'test_*.py' -v
```

O teste de navegador é habilitado explicitamente:

```bash
python -m pip install playwright==1.64.1
python -m playwright install --with-deps chromium
RUN_BROWSER_TESTS=1 python manage.py test questoes.test_browser --settings=gerador_provas.test_settings --verbosity=2
```

`BROWSER_EXECUTABLE` permite usar Chromium já instalado e `BROWSER_SCREENSHOT`
permite capturar a confirmação com os dados sintéticos do teste. A CI verifica
Python 3.12/3.13, migrações, concorrência no SQLite com arquivo real, regressões,
backup, fluxo no navegador, Ruff e vulnerabilidades das dependências.

A suíte original não continha testes executáveis. Nenhum teste local equivale a
verificação autenticada do PythonAnywhere, PostgreSQL ou MySQL.
