# Endereço do arquivo: questoes/models.py

from django.db import models

# Documentação:
# Este modelo representa os períodos do curso (ex: 1º Período, 2º Período).
class Periodo(models.Model):
    nome = models.CharField(max_length=100, unique=True, help_text="Ex: 1º Período")

    def __str__(self):
        return self.nome

# Documentação:
# Este modelo representa os componentes curriculares (disciplinas).
# Cada componente está associado a um período.
class ComponenteCurricular(models.Model):
    nome = models.CharField(max_length=200, help_text="Ex: Anatomia Humana")
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name="componentes")
    # O administrador definirá o número de questões para este componente na prova.
    numero_questoes_prova = models.PositiveIntegerField(default=5, help_text="Número de questões a serem selecionadas para a prova.")

    def __str__(self):
        return f"{self.nome} ({self.periodo.nome})"

# Documentação:
# Este é o modelo principal, que armazena cada questão enviada.
class Questao(models.Model):
    # Enum para o status de validação da questão.
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente de Validação'),
        ('APROVADA', 'Aprovada'),
        ('REPROVADA', 'Reprovada'),
    ]

    componente = models.ForeignKey(ComponenteCurricular, on_delete=models.CASCADE, related_name="questoes")
    texto_base = models.TextField(blank=True, null=True, help_text="Texto ou contexto que serve de base para a questão.")
    imagem = models.ImageField(upload_to='imagens_questoes/', blank=True, null=True, help_text="Imagem opcional para a questão.")
    enunciado = models.TextField(help_text="O enunciado ou pergunta principal da questão.")
    justificativa = models.TextField(help_text="Explicação detalhada sobre o gabarito e as alternativas.")
    
    # Campo para controle do administrador.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    
    def __str__(self):
        # Retorna os primeiros 50 caracteres do enunciado para fácil identificação.
        return self.enunciado[:50] + "..."

# Documentação:
# Este modelo armazena as alternativas de uma questão.
# Cada questão pode ter várias alternativas associadas.
class Alternativa(models.Model):
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE, related_name="alternativas")
    texto = models.CharField(max_length=500, help_text="Texto da alternativa (A, B, C, D ou E).")
    eh_correta = models.BooleanField(default=False, help_text="Marque esta opção se esta for a alternativa correta (gabarito).")

    def __str__(self):
        return self.texto