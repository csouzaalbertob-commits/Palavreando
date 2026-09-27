# autentica/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from email_validator import validate_email, EmailNotValidError
from .models import PerfilProfessor

DOMAIN_PROFESSOR = "@escola.seduc.pa.gov.br"
DOMAIN_ALUNO = "@aluno.seduc.pa.gov.br"


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="E-mail ou Usuário Institucional",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'exemplo@escola.seduc.pa.gov.br ou seu_usuario'
        })
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Sua senha'})
    )

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()

        # Validação do Domínio Institucional após autenticação com sucesso
        if user:
            email = user.email.lower()
            if not (email.endswith(DOMAIN_PROFESSOR) or email.endswith(DOMAIN_ALUNO)):
                raise forms.ValidationError(
                    "Acesso negado. Apenas contas institucionais (@escola.seduc.pa.gov.br ou @aluno.seduc.pa.gov.br) têm permissão."
                )
        return cleaned_data


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
    email = forms.EmailField(
        label="E-mail Institucional",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'exemplo@escola.seduc.pa.gov.br'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if not email.endswith(DOMAIN_PROFESSOR):
            raise forms.ValidationError(
                f"O e-mail deve pertencer ao domínio institucional ({DOMAIN_PROFESSOR})."
            )

        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está sendo utilizado por outro usuário.")

        try:
            valid = validate_email(email, check_deliverability=True)
            email = valid.normalized
        except EmailNotValidError:
            raise forms.ValidationError("O e-mail informado não pôde ser verificado no servidor institucional.")

        return email


class CadastroProfessorForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=30, required=True)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=True)

    email = forms.EmailField(
        label="E-mail Institucional (@escola.seduc.pa.gov.br)",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'id@escola.seduc.pa.gov.br'
        })
    )

    matricula = forms.CharField(
        label="Matrícula",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite sua matrícula'})
    )
    telefone = forms.CharField(label="Telefone", max_length=20, required=False)
    disciplina = forms.CharField(label="Disciplina", max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if not email.endswith(DOMAIN_PROFESSOR):
            raise forms.ValidationError(
                f"Apenas e-mails institucionais finalizados com {DOMAIN_PROFESSOR} são permitidos."
            )

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail institucional já está cadastrado no sistema.")

        try:
            valid = validate_email(email, check_deliverability=True)
            email = valid.normalized
        except EmailNotValidError:
            raise forms.ValidationError(
                "O e-mail informado não pôde ser verificado no servidor institucional ou não existe."
            )

        return email

    def clean_matricula(self):
        matricula = self.cleaned_data.get('matricula', '').strip()

        if PerfilProfessor.objects.filter(matricula=matricula).exists():
            raise forms.ValidationError("Esta matrícula já está cadastrada para outro professor.")

        return matricula

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            PerfilProfessor.objects.create(
                usuario=user,
                matricula=self.cleaned_data['matricula'],
                telefone=self.cleaned_data['telefone'],
                disciplina=self.cleaned_data['disciplina']
            )
        return user