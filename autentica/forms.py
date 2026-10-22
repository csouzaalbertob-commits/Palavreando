from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from email_validator import EmailNotValidError, validate_email
from autentica.models import DRE, Cidade, Escola, PerfilProfessor
#from .models import DRE, Cidade, Escola, PerfilProfessor

DOMAIN_PROFESSOR = "@escola.seduc.pa.gov.br"
DOMAIN_ALUNO = "@aluno.seduc.pa.gov.br"

class EditarPerfilForm(
    forms.ModelForm
):  # Use o nome correto da sua classe de form
  # ... seus campos continuam aqui ...

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # 1. Define os querysets iniciais vazios para dependências encadeadas
    self.fields['dre'].queryset = DRE.objects.none()
    self.fields['escola'].queryset = Escola.objects.none()

    cidade_id = None

    # 2. Tenta obter a cidade_id a partir dos dados do formulário (POST/GET)
    if self.data:
      cidade_id = self.data.get('cidade')
    # 3. Se não houver POST, tenta obter do objeto/perfil existente
    elif self.instance and hasattr(self.instance, 'cidade') and self.instance.cidade:
      cidade_id = self.instance.cidade.id

    # 4. Se encontrou a cidade, popula as DREs correspondentes
    if cidade_id:
      try:
        self.fields['dre'].queryset = DRE.objects.filter(
            cidade_id=cidade_id
        ).order_by('nome')
      except (ValueError, TypeError):
        pass

    # 5. Tratamento semelhante para a Escola (se depender de DRE ou Cidade)
    dre_id = None
    if self.data:
      dre_id = self.data.get('dre')
    elif self.instance and hasattr(self.instance, 'dre') and self.instance.dre:
      dre_id = self.instance.dre.id

    if dre_id:
      try:
        self.fields['escola'].queryset = Escola.objects.filter(
            dre_id=dre_id
        ).order_by('nome')
      except (ValueError, TypeError):
        pass
      
class LoginForm(AuthenticationForm):
  username = forms.CharField(
      label="E-mail ou Usuário Institucional",
      widget=forms.TextInput(
          attrs={
              "class": "form-control",
              "placeholder": "exemplo@escola.seduc.pa.gov.br ou seu_usuario",
          }
      ),
  )
  password = forms.CharField(
      label="Senha",
      widget=forms.PasswordInput(
          attrs={"class": "form-control", "placeholder": "Sua senha"}
      ),
  )

  def clean(self):
    cleaned_data = super().clean()
    user = self.get_user()

    if user:
      email = user.email.lower()
      if not (
          email.endswith(DOMAIN_PROFESSOR) or email.endswith(DOMAIN_ALUNO)
      ):
        raise forms.ValidationError(
            "Acesso negado. Apenas contas institucionais (@escola.seduc.pa.gov.br"
            " ou @aluno.seduc.pa.gov.br) têm permissão."
        )
    return cleaned_data


class PerfilProfessorForm(forms.ModelForm):

  class Meta:
    model = PerfilProfessor
    fields = [
        "matricula",
        "telefone",
        "disciplina",
        "cidade",
        "dre",
        "escola",
        "foto",
    ]
    widgets = {
        "matricula": forms.TextInput(attrs={"class": "form-control"}),
        "telefone": forms.TextInput(attrs={"class": "form-control"}),
        "disciplina": forms.TextInput(attrs={"class": "form-control"}),
        "cidade": forms.Select(
            attrs={"class": "form-select", "id": "id_cidade"}
        ),
        "dre": forms.Select(attrs={"class": "form-select", "id": "id_dre"}),
        "escola": forms.Select(
            attrs={"class": "form-select", "id": "id_escola"}
        ),
        "foto": forms.FileInput(attrs={"class": "form-control"}),
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # 1. Garante que os campos fiquem vazios por padrão
    self.fields["cidade"].queryset = Cidade.objects.all().order_by("nome")
    self.fields["dre"].queryset = DRE.objects.none()
    self.fields["escola"].queryset = Escola.objects.none()

    # 2. Resgate seguro de cidade_id (evita UnboundLocalError)
    cidade_id = None
    if self.data and self.data.get("cidade"):
      cidade_id = self.data.get("cidade")
    elif self.instance and self.instance.cidade_id:
      cidade_id = self.instance.cidade_id

    if cidade_id:
      try:
        self.fields["dre"].queryset = DRE.objects.filter(
            cidade_id=int(cidade_id)
        ).order_by("nome")
      except (ValueError, TypeError):
        pass

    # 3. Resgate seguro de dre_id
    dre_id = None
    if self.data and self.data.get("dre"):
      dre_id = self.data.get("dre")
    elif self.instance and self.instance.dre_id:
      dre_id = self.instance.dre_id

    if dre_id:
      try:
        self.fields["escola"].queryset = Escola.objects.filter(
            dre_id=int(dre_id)
        ).order_by("nome")
      except (ValueError, TypeError):
        pass


class AtualizarProfessorForm(forms.ModelForm):
  first_name = forms.CharField(
      label="Nome",
      max_length=150,
      widget=forms.TextInput(
          attrs={"class": "form-control", "placeholder": "Seu nome"}
      ),
  )
  last_name = forms.CharField(
      label="Sobrenome",
      max_length=150,
      widget=forms.TextInput(
          attrs={"class": "form-control", "placeholder": "Seu sobrenome"}
      ),
  )
  email = forms.EmailField(
      label="E-mail Institucional",
      widget=forms.EmailInput(
          attrs={
              "class": "form-control",
              "placeholder": "exemplo@escola.seduc.pa.gov.br",
          }
      ),
  )

  class Meta:
    model = User
    fields = ["first_name", "last_name", "email"]

  def clean_email(self):
    email = self.cleaned_data.get("email", "").strip().lower()

    if not email.endswith(DOMAIN_PROFESSOR):
      raise forms.ValidationError(
          f"O e-mail deve pertencer ao domínio institucional ({DOMAIN_PROFESSOR})."
      )

    if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
      raise forms.ValidationError(
          "Este e-mail já está sendo utilizado por outro usuário."
      )

    try:
      valid = validate_email(email, check_deliverability=True)
      email = valid.normalized
    except EmailNotValidError:
      raise forms.ValidationError(
          "O e-mail informado não pôde ser verificado no servidor institucional."
      )

    return email


class CadastroProfessorForm(UserCreationForm):
  first_name = forms.CharField(
      label="Nome",
      max_length=30,
      required=True,
      widget=forms.TextInput(
          attrs={"class": "form-control", "placeholder": "Digite seu nome"}
      ),
  )
  last_name = forms.CharField(
      label="Sobrenome",
      max_length=150,
      required=True,
      widget=forms.TextInput(
          attrs={"class": "form-control", "placeholder": "Digite seu sobrenome"}
      ),
  )

  email = forms.EmailField(
      label="E-mail Institucional (@escola.seduc.pa.gov.br)",
      required=True,
      widget=forms.EmailInput(
          attrs={
              "class": "form-control",
              "placeholder": "id@escola.seduc.pa.gov.br",
          }
      ),
  )

  matricula = forms.CharField(
      label="Matrícula",
      max_length=20,
      required=True,
      widget=forms.TextInput(
          attrs={"class": "form-control", "placeholder": "Digite sua matrícula"}
      ),
  )
  telefone = forms.CharField(
      label="Telefone",
      max_length=20,
      required=False,
      widget=forms.TextInput(
          attrs={"class": "form-control", "placeholder": "(91) 9xxxx-xxxx"}
      ),
  )
  disciplina = forms.CharField(
      label="Disciplina",
      max_length=100,
      required=False,
      widget=forms.TextInput(
          attrs={"class": "form-control", "placeholder": "Ex: Língua Portuguesa"}
      ),
  )

  cidade = forms.ModelChoiceField(
      queryset=Cidade.objects.all().order_by("nome"),
      required=False,
      empty_label="Selecione a Cidade (Opcional)",
      widget=forms.Select(attrs={"class": "form-select", "id": "id_cidade"}),
  )
  dre = forms.ModelChoiceField(
      queryset=DRE.objects.none(),
      required=False,
      empty_label="Selecione a DRE (Opcional)",
      widget=forms.Select(attrs={"class": "form-select", "id": "id_dre"}),
  )
  escola = forms.ModelChoiceField(
      queryset=Escola.objects.none(),
      required=False,
      empty_label="Selecione a Escola (Opcional)",
      widget=forms.Select(attrs={"class": "form-select", "id": "id_escola"}),
  )

  class Meta(UserCreationForm.Meta):
    model = User
    fields = ("username", "first_name", "last_name", "email")

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    if "cidade" in self.data:
      try:
        cidade_id = int(self.data.get("cidade"))
        self.fields["dre"].queryset = DRE.objects.filter(
            cidade_id=cidade_id
        ).order_by("nome")
      except (ValueError, TypeError):
        pass

    if "dre" in self.data:
      try:
        dre_id = int(self.data.get("dre"))
        self.fields["escola"].queryset = Escola.objects.filter(
            dre_id=dre_id
        ).order_by("nome")
      except (ValueError, TypeError):
        pass

  def clean_email(self):
    email = self.cleaned_data.get("email", "").strip().lower()

    if not email.endswith(DOMAIN_PROFESSOR):
      raise forms.ValidationError(
          f"Apenas e-mails institucionais finalizados com {DOMAIN_PROFESSOR} são"
          " permitidos."
      )

    if User.objects.filter(email=email).exists():
      raise forms.ValidationError(
          "Este e-mail institucional já está cadastrado no sistema."
      )

    try:
      valid = validate_email(email, check_deliverability=True)
      email = valid.normalized
    except EmailNotValidError:
      raise forms.ValidationError(
          "O e-mail informado não pôde ser verificado no servidor"
          " institucional ou não existe."
      )

    return email

  def clean_matricula(self):
    matricula = self.cleaned_data.get("matricula", "").strip()

    if PerfilProfessor.objects.filter(matricula=matricula).exists():
      raise forms.ValidationError(
          "Esta matrícula já está cadastrada para outro professor."
      )

    return matricula

  def save(self, commit=True):
    user = super().save(commit=False)
    user.first_name = self.cleaned_data["first_name"]
    user.last_name = self.cleaned_data["last_name"]
    user.email = self.cleaned_data["email"]

    if commit:
      user.save()
      PerfilProfessor.objects.create(
          usuario=user,
          matricula=self.cleaned_data["matricula"],
          telefone=self.cleaned_data.get("telefone"),
          disciplina=self.cleaned_data.get("disciplina"),
          cidade=self.cleaned_data.get("cidade"),
          dre=self.cleaned_data.get("dre"),
          escola=self.cleaned_data.get("escola"),
      )
    return user