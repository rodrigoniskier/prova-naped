# prova-naped

Banco de questões e gerador de provas em Django, com área administrativa para validação e importação
entre componentes curriculares.

## Problema, público e resultado

**Problema.** Docentes precisam reunir questões por componente curricular, validá-las e sortear provas, e reaproveitar itens entre componentes sem perder o histórico de onde vieram.

**Para quem.** Docentes e coordenação de um curso que mantêm o banco de questões de vários componentes.

**O que entrega.** Submissão de questões com alternativas e gabarito; validação por status (pendente, aprovada, reprovada); organização por período e componente; geração de prova com número configurável de questões; importação de questões entre componentes do mesmo semestre com histórico auditável.

**Tecnologias.** Python, Django 5.2, SQL, Jazzmin (admin), GitHub Actions, PythonAnywhere.

**Qualidade e evidências.** 41 funções de teste automatizadas; CI em Python 3.12 e 3.13 com verificação de migrações, testes e teste de navegador; documentação de importação e de deploy em `docs/`. Licença MIT.

## Estrutura

- `questoes/`: modelos (semestre letivo, período, componente, questão, alternativa e importação),
  formulários, importação e administração.
- `gerador_provas/`: configuração do projeto Django.
- `docs/`: [importação de questões](docs/importacao-questoes.md) e
  [deploy no PythonAnywhere](docs/deploy-pythonanywhere.md).

## Executar localmente

Requer Python 3.12 ou superior.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DEBUG=True
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Testes

```bash
python manage.py test --settings=gerador_provas.test_settings
```

## Segurança

Defina sempre `DJANGO_SECRET_KEY` em produção e mantenha `DEBUG` desligado. Não versione bancos de
dados, mídias nem arquivos `.env`.
