# 🌍 Orbis - Plataforma de Tradução em Tempo Real

Aplicação web de tradução simultânea com IA, suportando múltiplos idiomas e clonagem de voz.

---

## 📚 Documentação de Deploy

### 🎯 **Start Aqui:**
- **[QUICK_START.md](./QUICK_START.md)** - Resumo executivo (5 minutos)
- **[PLATFORM_COMPARISON.md](./PLATFORM_COMPARISON.md)** - Comparação de plataformas

### 🚀 **Guias de Deploy:**

#### **Railway.app** ⭐ RECOMENDADO
- **[DEPLOY_RAILWAY.md](./DEPLOY_RAILWAY.md)** - Deploy com Redis avançado
- ✅ $5/mês
- ✅ Redis customizado (redis.conf)
- ✅ 20 minutos de configuração

#### **Render.com** (Básico)
- **[DEPLOY_GUIDE.md](./DEPLOY_GUIDE.md)** - Deploy grátis simples
- ✅ 100% grátis
- ⚠️ Redis básico (sem customização)
- ✅ 30 minutos de configuração

#### **Fly.io** (Avançado)
- **[DEPLOY_FLY.md](./DEPLOY_FLY.md)** - Deploy grátis avançado
- ✅ 100% grátis
- ✅ Redis customizado
- ⚠️ 2 horas de configuração

---

## 🏗️ Arquitetura

```
Frontend (React + Vite)
    ↓
Backend (FastAPI + Python)
    ↓
├─ PostgreSQL (Database)
├─ Redis (Cache + Sessions)
└─ ML Models (Whisper + NLLB + TTS)
```

---

## 🛠️ Tecnologias

- **Frontend:** React, TypeScript, Vite, TailwindCSS
- **Backend:** Python, FastAPI, Uvicorn
- **Database:** PostgreSQL
- **Cache:** Redis (com configurações avançadas)
- **ML:** Whisper (ASR), NLLB (MT), Coqui TTS
- **Deploy:** Railway, Render, ou Fly.io

---

## 🔧 Desenvolvimento Local

### Pré-requisitos:
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Quick Start:

```bash
# 1. Clonar
git clone https://github.com/seu-usuario/orbis.git
cd orbis

# 2. Copiar .env
cp .env.example .env
# Editar .env com suas configurações

# 3. Iniciar services (Docker)
docker-compose up -d

# 4. Instalar dependências backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# 5. Instalar dependências frontend
cd frontend
npm install

# 6. Iniciar backend
cd ..
uvicorn backend.main:app --reload

# 7. Iniciar frontend (nova janela)
cd frontend
npm run dev
```

Abra: `http://localhost:5173`

---

## 📋 Arquivos de Configuração

### Desenvolvimento:
- `.env.example` - Template de variáveis locais
- `docker-compose.yml` - Services para dev local
- `redis.conf` - Configuração Redis customizada

### Produção:
- `.env.production.example` - Template para produção
- `docker-compose.production.yml` - Services otimizados
- `Dockerfile.railway` - Imagem otimizada
- `railway.json` - Config Railway
- `generate_secrets.py` - Gera senhas seguras

---

## 🔐 Segurança

### Gerar chaves seguras:

```bash
# Rodar script incluído
python generate_secrets.py

# Ou manualmente
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Variáveis críticas:
- `SECRET_KEY` - Criptografia geral
- `JWT_SECRET` - Autenticação JWT
- `POSTGRES_PASSWORD` - Senha database
- `REDIS_PASSWORD` - Senha Redis

**NUNCA** commite arquivos `.env` reais!

---

## 🧪 Testes

```bash
# Backend
pytest

# Frontend
cd frontend
npm run test
```

---

## 📊 Features

- ✅ Tradução em tempo real (50+ idiomas)
- ✅ Reconhecimento de voz (Whisper)
- ✅ Text-to-Speech multilíngue
- ✅ Clonagem de voz
- ✅ Salas colaborativas
- ✅ Autenticação JWT
- ✅ Cache Redis avançado
- ✅ Analytics em tempo real
- ✅ Gamificação
- ⚠️ Upload de áudio (WIP)
- ⚠️ Marketplace de vozes (Planejado)

---

## 💰 Custos de Deploy

| Plataforma | Grátis | Pago | Redis Config |
|------------|--------|------|--------------|
| Railway | $5 crédito | $5/mês | ✅ Completo |
| Render | ✅ Sim | $7/mês | ⚠️ Básico |
| Fly.io | ✅ Sim | $5/mês | ✅ Completo |

**Recomendação:** Railway ($5/mês) para melhor custo-benefício

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📝 Licença

Este projeto é privado. Entre em contato para licenciamento.

---

## 🔗 Links Úteis

- **Documentação completa:** [Wiki](./wiki)
- **Roadmap:** [ROADMAP.md](./ROADMAP.md)
- **Changelog:** [CHANGELOG.md](./CHANGELOG.md)
- **Issues:** [GitHub Issues](https://github.com/seu-usuario/orbis/issues)

---

## 📞 Suporte

- 📧 Email: suporte@orbis.app
- 💬 Discord: [Orbis Community](#)
- 📖 Docs: [docs.orbis.app](#)

---

**Versão:** 2.0.0  
**Última atualização:** 2025-11-24  
**Status:** 🚀 Em produção

---

## 🎯 Próximos Passos

1. **Para usuários novos:**
   - Leia [QUICK_START.md](./QUICK_START.md)
   - Escolha plataforma em [PLATFORM_COMPARISON.md](./PLATFORM_COMPARISON.md)
   - Siga o guia de deploy correspondente

2. **Para desenvolvedores:**
   - Configure ambiente local (veja acima)
   - Leia [CONTRIBUTING.md](./CONTRIBUTING.md)
   - Veja issues abertas

3. **Para deploy:**
   - Gere senhas: `python generate_secrets.py`
   - Escolha: Railway, Render, ou Fly.io
   - Siga guia específico

---

Feito com ❤️ pela equipe Orbis
