# questoes/admin.py

from django.contrib import admin
from .models import Periodo, ComponenteCurricular, Questao, Alternativa

# Documentação:
# A classe 'AlternativaInline' permite que as alternativas sejam visualizadas
# e editadas diretamente na página de edição da Questão.
# 'TabularInline' mostra os campos em um formato de tabela, mais compacto.
class AlternativaInline(admin.TabularInline):
    model = Alternativa
    # Quantos campos de alternativa em branco queremos mostrar além dos já existentes.
    extra = 1

# Documentação:
# Esta classe personaliza como o modelo 'Questao' é exibido e se comporta
# na interface de administração.
@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    # 'inlines' conecta a classe AlternativaInline a esta view.
    inlines = [AlternativaInline]

    # 'list_display' define quais colunas aparecerão na lista de questões.
    list_display = ('enunciado', 'componente', 'status')

    # 'list_filter' cria uma barra lateral de filtros.
    list_filter = ('status', 'componente__periodo', 'componente')

    # 'search_fields' adiciona um campo de busca.
    search_fields = ('enunciado', 'texto_base')

    # 'actions' adiciona opções no menu "Ações" para operar em múltiplos itens.
    actions = ['aprovar_questoes', 'reprovar_questoes']

    def aprovar_questoes(self, request, queryset):
        # Esta ação atualiza o status de todas as questões selecionadas para 'APROVADA'.
        queryset.update(status='APROVADA')
        self.message_user(request, "As questões selecionadas foram aprovadas com sucesso.")
    aprovar_questoes.short_description = "Aprovar questões selecionadas"

    def reprovar_questoes(self, request, queryset):
        # Esta ação atualiza o status de todas as questões selecionadas para 'REPROVADA'.
        queryset.update(status='REPROVADA')
        self.message_user(request, "As questões selecionadas foram reprovadas.")
    reprovar_questoes.short_description = "Reprovar questões selecionadas"


# Registramos os outros modelos da forma padrão, pois não precisam de tanta personalização.
admin.site.register(Periodo)
admin.site.register(ComponenteCurricular)

# O modelo Alternativa não precisa ser registrado separadamente,
# pois ele já é gerenciável através da QuestaoAdmin.