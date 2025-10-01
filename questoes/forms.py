# questoes/forms.py

from django import forms
from .models import Questao, Alternativa

# Classes CSS reutilizáveis para os campos
text_input_classes = 'w-full text-base px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white transition-all duration-200'
textarea_classes = text_input_classes + ' custom-scrollbar'
select_classes = text_input_classes
checkbox_classes = 'rounded border-gray-300 text-primary focus:ring-primary'
file_input_classes = 'w-full text-base px-4 py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white transition-all duration-200'

class QuestaoForm(forms.ModelForm):
    class Meta:
        model = Questao
        fields = ['componente', 'texto_base', 'imagem', 'enunciado', 'justificativa']
        widgets = {
            'componente': forms.Select(attrs={'class': select_classes}),
            'texto_base': forms.Textarea(attrs={'class': textarea_classes, 'rows': 6, 'placeholder': 'Digite o texto-base da questão...'}),
            'imagem': forms.FileInput(attrs={'class': file_input_classes}),
            'enunciado': forms.Textarea(attrs={'class': textarea_classes, 'rows': 4, 'placeholder': 'Digite o enunciado da questão...'}),
            'justificativa': forms.Textarea(attrs={'class': textarea_classes, 'rows': 6, 'placeholder': 'Digite a justificativa da questão...'}),
        }
        labels = {
            'componente': '', 'texto_base': '', 'imagem': '', 'enunciado': '', 'justificativa': ''
        }

class AlternativaForm(forms.ModelForm):
    class Meta:
        model = Alternativa
        fields = ['texto', 'eh_correta']
        widgets = {
            'texto': forms.TextInput(attrs={'class': text_input_classes, 'placeholder': 'Digite o texto da alternativa...'}),
            'eh_correta': forms.CheckboxInput(attrs={'class': checkbox_classes}),
        }