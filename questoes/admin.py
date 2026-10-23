# questoes/admin.py

from django.contrib import admin
from django.urls import path

from .importacao_admin import importar_view
from .models import (
    Alternativa,
    ComponenteCurricular,
    ImportacaoQuestao,
    Periodo,
    Questao,
    SemestreLetivo,
)


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


@admin.register(SemestreLetivo)
class SemestreLetivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')
    list_filter = ('ativo',)
    filter_horizontal = ('componentes',)
    search_fields = ('nome',)


@admin.register(ImportacaoQuestao)
class ImportacaoQuestaoAdmin(admin.ModelAdmin):
    list_display = ('origem_identificador', 'copia', 'receptor', 'semestre', 'responsavel', 'criada_em')
    list_select_related = ('copia', 'receptor__periodo', 'semestre', 'responsavel')
    list_filter = ('semestre', 'receptor')
    readonly_fields = tuple(field.name for field in ImportacaoQuestao._meta.fields)
    change_list_template = 'admin/questoes/importacaoquestao/change_list.html'
    actions = None

    def get_urls(self):
        return [path('importar/', self.admin_site.admin_view(self.importar), name='questoes_importar')] + super().get_urls()

    def importar(self, request):
        return importar_view(request, admin_site=self.admin_site)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
