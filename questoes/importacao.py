"""Clonagem transacional, com recibo único e compensação de arquivos novos."""

import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Prefetch

from .models import Alternativa, ComponenteCurricular, ImportacaoQuestao, Questao, SemestreLetivo

logger = logging.getLogger(__name__)
LIMITE_IMPORTACAO = 500
PERMISSOES = ("questoes.importar_questoes", "questoes.view_questao", "questoes.add_questao")


def pode_importar(usuario):
    return usuario.is_active and usuario.is_staff and usuario.has_perms(PERMISSOES)


@dataclass(frozen=True)
class ResultadoImportacao:
    importadas: int
    ignoradas: int


def normalizar_ids(ids):
    try:
        valores = list(ids)
        if not valores or len(valores) > LIMITE_IMPORTACAO:
            raise ValueError
        if any(
            not (
                type(item) is int or (isinstance(item, str) and item.isascii() and item.isdecimal())
            )
            for item in valores
        ):
            raise ValueError
        resultado = [int(item) for item in valores]
        if any(item <= 0 for item in resultado) or len(set(resultado)) != len(resultado):
            raise ValueError
        return sorted(resultado)
    except (ValueError, TypeError, OverflowError):
        raise ValidationError(f"Selecione de 1 a {LIMITE_IMPORTACAO} questões distintas.") from None


def importar_questoes(*, usuario, semestre_id, doador_id, receptor_id, questao_ids):
    if not pode_importar(usuario):
        raise PermissionDenied
    ids = normalizar_ids(questao_ids)
    arquivos_criados = []
    try:
        # durable impede que um chamador reverta o banco depois da compensação
        # dos arquivos. A view não usa ATOMIC_REQUESTS nem outra transação externa.
        with transaction.atomic(durable=True):
            # A primeira operação já adquire o bloqueio de escrita do SQLite.
            # Também serializa os importadores deste semestre em PostgreSQL/MySQL.
            if not SemestreLetivo.objects.filter(pk=semestre_id, ativo=True).update(
                ativo=F("ativo")
            ):
                raise ValidationError("O semestre letivo deve estar ativo.")
            componentes = {
                c.pk: c
                for c in ComponenteCurricular.objects.select_for_update()
                .filter(pk__in=[doador_id, receptor_id])
                .order_by("pk")
            }
            if doador_id == receptor_id or len(componentes) != 2:
                raise ValidationError("Escolha componentes distintos e válidos.")
            vinculos = SemestreLetivo.componentes.through.objects.select_for_update().filter(
                semestreletivo_id=semestre_id,
                componentecurricular_id__in=componentes,
            )
            if len(list(vinculos)) != 2:
                raise ValidationError("Os componentes devem pertencer ao mesmo semestre ativo.")
            originais = list(
                Questao.objects.select_for_update()
                .filter(
                    pk__in=ids,
                    componente_id=doador_id,
                )
                .order_by("pk")
                .prefetch_related(
                    Prefetch(
                        "alternativas",
                        queryset=Alternativa.objects.select_for_update().order_by("pk"),
                    )
                )
            )
            if len(originais) != len(ids):
                raise ValidationError("Há questões inválidas ou que não pertencem ao doador.")
            existentes = set(
                ImportacaoQuestao.objects.filter(
                    origem_identificador__in=ids,
                    receptor_id=receptor_id,
                ).values_list("origem_identificador", flat=True)
            )
            for origem in originais:
                if origem.pk in existentes:
                    continue
                copia = Questao(
                    componente_id=receptor_id,
                    texto_base=origem.texto_base,
                    enunciado=origem.enunciado,
                    justificativa=origem.justificativa,
                    status="PENDENTE",
                )
                if origem.imagem:
                    storage = origem.imagem.storage
                    nome = f"imagens_questoes/importadas/{uuid4().hex}{PurePosixPath(origem.imagem.name).suffix}"
                    with storage.open(origem.imagem.name, "rb") as arquivo:
                        nome_salvo = storage.save(nome, arquivo)
                    arquivos_criados.append((storage, nome_salvo))
                    copia.imagem = nome_salvo
                copia.save()
                Alternativa.objects.bulk_create(
                    [
                        Alternativa(questao=copia, texto=a.texto, eh_correta=a.eh_correta)
                        for a in origem.alternativas.all()
                    ]
                )
                ImportacaoQuestao.objects.create(
                    origem=origem,
                    origem_identificador=origem.pk,
                    componente_origem=componentes[doador_id].nome,
                    copia=copia,
                    receptor_id=receptor_id,
                    semestre_id=semestre_id,
                    responsavel=usuario,
                )
        return ResultadoImportacao(len(ids) - len(existentes), len(existentes))
    except Exception:
        for storage, nome in arquivos_criados:
            try:
                storage.delete(nome)
            except Exception:
                logger.exception("Falha ao remover arquivo de importação revertida: %s", nome)
        raise
