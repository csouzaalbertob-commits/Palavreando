from django import forms
from .models import Palavra, Frase

app_name = 'palavra'

class PalavraForm(forms.ModelForm):
    class Meta:
        model = Palavra
        fields = ['texto', 'tipo', 'dificuldade']
        widgets = {
            'texto': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Digite a palavra ou pseudopalavra...'
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'dificuldade': forms.Select(attrs={'class': 'form-select'}),
        }

#para o Ditado
class FraseForm(forms.ModelForm):

  class Meta:
    model = Frase
    fields = ['nivel', 'texto']
    widgets = {
        'nivel': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        'texto': forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': (
                    'Digite aqui a frase ou parágrafo completo para o'
                    ' ditado...'
                ),
            }
        ),
    }
    labels = {
        'nivel': 'Nível de Dificuldade',
        'texto': 'Frase / Parágrafo do Ditado',
    }