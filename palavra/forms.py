from django import forms
from .models import Palavra

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