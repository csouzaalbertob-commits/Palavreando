# alunos/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import PerfilProfessor
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.models import User

app_name = 'autentica'

class PerfilProfessorForm(forms.ModelForm):
    class Meta:
        model = PerfilProfessor
        fields = ['matricula', 'telefone', 'disciplina', 'escola', 'foto']
        widgets = {
            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'disciplina': forms.TextInput(attrs={'class': 'form-control'}),
            'escola': forms.TextInput(attrs={'class': 'form-control'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
        }

class AtualizarProfessorForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu nome'})
    )
    last_name = forms.CharField(
        label="Sobrenome",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu sobrenome'})
    )
    email = forms.EmailInput(
        attrs={'class': 'form-control', 'placeholder': 'Seu e-mail'}
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Verifica se o e-mail já pertence a outro usuário
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está sendo utilizado por outro usuário.")
        return email
    
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu usuário'})
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Sua senha'})
    )

class CadastroProfessorForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=30, required=True)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=True)
    email = forms.EmailField(label="E-mail", required=True)
    
    # Campos do Perfil
    matricula = forms.CharField(label="Matrícula", max_length=20, required=True)
    telefone = forms.CharField(label="Telefone", max_length=20, required=False)
    disciplina = forms.CharField(label="Disciplina", max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Cria o perfil associado ao usuário
            PerfilProfessor.objects.create(
                usuario=user,
                matricula=self.cleaned_data['matricula'],
                telefone=self.cleaned_data['telefone'],
                disciplina=self.cleaned_data['disciplina']
            )
        return user