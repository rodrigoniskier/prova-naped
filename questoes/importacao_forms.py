from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.db.models import Count

from .importacao import LIMITE_IMPORTACAO
from .models import ComponenteCurricular, Questao, SemestreLetivo

SALT = "questoes.importacao.v1"


class ComponenteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj} — {obj.total_questoes} questões"


class ContextoImportacaoForm(forms.Form):
    semestre = forms.ModelChoiceField(
        label="Semestre letivo ativo", queryset=SemestreLetivo.objects.none()
    )
    doador = ComponenteChoiceField(
        label="Componente doador", queryset=ComponenteCurricular.objects.none()
    )
    receptor = ComponenteChoiceField(
        label="Componente receptor", required=False, queryset=ComponenteCurricular.objects.none()
    )

    def __init__(self, *args, exigir_doador=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doador"].required = exigir_doador
        self.fields["semestre"].queryset = SemestreLetivo.objects.filter(ativo=True)
        if self.is_bound:
            try:
                semestre_id = int(self.data.get("semestre", ""))
                doador_id = int(self.data.get("doador", "") or 0)
            except (ValueError, TypeError):
                return
            componentes = (
                ComponenteCurricular.objects.filter(
                    semestres_letivos__id=semestre_id,
                    semestres_letivos__ativo=True,
                )
                .select_related("periodo")
                .annotate(total_questoes=Count("questoes"))
                .order_by("nome", "pk")
            )
            self.fields["doador"].queryset = componentes
            self.fields["receptor"].queryset = componentes.exclude(pk=doador_id)


def assinar_estado(*, chave, contexto, selecionadas, visiveis, fase="selecao"):
    return signing.dumps(
        {
            "semestre": contexto["semestre"].pk,
            "doador": contexto["doador"].pk,
            "receptor": contexto["receptor"].pk if contexto.get("receptor") else None,
            "selecionadas": sorted(selecionadas),
            "visiveis": list(visiveis),
            "fase": fase,
        },
        key=chave,
        salt=SALT,
        compress=True,
    )


class SelecaoImportacaoForm(forms.Form):
    estado = forms.CharField(max_length=30000, widget=forms.HiddenInput)
    marcadas = forms.TypedMultipleChoiceField(required=False, coerce=int)
    busca = forms.CharField(required=False, max_length=200)
    status = forms.ChoiceField(
        required=False, choices=[("", "Todos os status"), *Questao.STATUS_CHOICES]
    )
    pagina = forms.IntegerField(min_value=1, max_value=1000000, required=False)
    acao = forms.ChoiceField(
        choices=[
            (a, a)
            for a in (
                "pagina",
                "filtrar",
                "confirmar",
                "importar",
                "voltar",
                "selecionar_filtradas",
                "limpar_todas",
            )
        ]
    )

    def __init__(self, *args, contexto, chave, **kwargs):
        self.contexto = contexto
        super().__init__(*args, **kwargs)
        try:
            self.estado = signing.loads(
                self.data.get("estado", ""), key=chave, salt=SALT, max_age=3600
            )
        except signing.BadSignature:
            self.estado = None
        if self.estado:
            self.fields["marcadas"].choices = [(i, str(i)) for i in self.estado["visiveis"]]

    def clean(self):
        dados = super().clean()
        estado = self.estado
        if not estado:
            raise ValidationError("Seleção expirada ou inválida. Recarregue os componentes.")
        if any(estado[campo] != self.contexto[campo].pk for campo in ("semestre", "doador")):
            raise ValidationError("A seleção pertence a outro semestre ou componente.")
        marcadas = dados.get("marcadas", [])
        if len(marcadas) != len(set(marcadas)):
            raise ValidationError("Não repita questões na mesma seleção.")
        acao = dados.get("acao")
        if acao == "importar" and (
            estado["fase"] != "confirmacao"
            or not self.contexto.get("receptor")
            or estado["receptor"] != self.contexto["receptor"].pk
        ):
            raise ValidationError("Confirme a operação e o componente receptor antes de importar.")
        if acao in ("confirmar", "importar") and not self.contexto.get("receptor"):
            raise ValidationError("Selecione um componente receptor.")
        selecionadas = (set(estado["selecionadas"]) - set(estado["visiveis"])) | set(
            dados.get("marcadas", [])
        )
        if len(selecionadas) > LIMITE_IMPORTACAO:
            raise ValidationError(f"Importe no máximo {LIMITE_IMPORTACAO} questões por operação.")
        if acao in ("confirmar", "importar") and not selecionadas:
            raise ValidationError("Selecione ao menos uma questão.")
        validas = Questao.objects.filter(
            pk__in=selecionadas, componente=self.contexto["doador"]
        ).count()
        if validas != len(selecionadas):
            raise ValidationError("A seleção contém questões removidas ou de outro componente.")
        dados["selecionadas"] = selecionadas
        return dados
