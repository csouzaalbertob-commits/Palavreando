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
        fields = ['texto', 'nivel']
        widgets = {
            'texto': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Digite a frase...'}),
            'nivel': forms.Select(choices=[(1, 'Nível 1 - Fácil'), (2, 'Nível 2 - Médio'), (3, 'Nível 3 - Difícil')], attrs={'class': 'form-select'}),
        }