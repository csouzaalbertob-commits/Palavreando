# Projeto Palavreando - Guia de Deploy (Ubuntu 26.04)

### 1. Clonar e criar o ambiente virtual
# 📚 Palavreando

O **Palavreando** é uma aplicação web desenvolvida em Django focada no gerenciamento de dados educacionais, alunos, palavras e informações do censo escolar.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.12+
- **Framework Web:** Django 5.x
- **Banco de Dados:** PostgreSQL
- **Ambiente Operacional Recomendado:** Ubuntu 22.04 / 24.04 / 26.04 LTS

---

## 📂 Estrutura de Módulos e Aplicativos

O projeto está dividido nos seguintes aplicativos Django:

- `alunos`: Gestão de cadastros e registros dos alunos.
- `autentica`: Controle de acessos, autenticação e permissões de usuários.
- `base` / `core`: Configurações centrais do sistema (settings, URLs globais e WSGI).
- `dados_censo`: Processamento e análise de dados provenientes do Censo Escolar.
- `palavra`: Módulo principal de vocabulário e atividades de linguagem.
- `sistema` / `sistemax`: Regras de negócio transversais e rotinas administrativas.

---

## 🚀 Guia de Instalação e Implantação (Deploy)

Siga as etapas abaixo para configurar o ambiente de desenvolvimento ou produção em um servidor **Ubuntu Linux**.

### 1. Pré-requisitos do Sistema
No terminal do servidor, instale os pacotes necessários do sistema e do PostgreSQL:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv postgresql postgresql-contrib libpq-dev git -y
