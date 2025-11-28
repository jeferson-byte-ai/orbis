# Guia de Gerenciamento de Usuários do Orbis

Este guia explica como listar e deletar usuários cadastrados no sistema Orbis.

## 📋 Opções Disponíveis

Você tem **duas formas** de gerenciar usuários:

1. **Via linha de comando** (CLI) - Mais rápido para tarefas simples
2. **Via API REST** - Perfeito para integração com interfaces web

---

## 🖥️ Via Linha de Comando (CLI)

### Pré-requisitos
- Backend do Orbis instalado
- Ambiente virtual ativado

### Comandos Disponíveis

#### 1. Listar todos os usuários
```bash
python -m backend.admin_users list
```

**Saída esperada:**
```
✅ Total de usuários cadastrados: 3

========================================================================================================
ID                                     Email                          Username             Nome Completo        
========================================================================================================
550e8400-e29b-41d4-a716-446655440000  usuario1@exemplo.com           user1                João Silva           
550e8400-e29b-41d4-a716-446655440001  usuario2@exemplo.com           user2                Maria Santos         
550e8400-e29b-41d4-a716-446655440002  usuario3@exemplo.com           user3                N/A                  
========================================================================================================
```

#### 2. Ver detalhes de um usuário específico
```bash
# Por email
python -m backend.admin_users info usuario@exemplo.com

# Por ID
python -m backend.admin_users info 550e8400-e29b-41d4-a716-446655440000
```

**Saída esperada:**
```
================================================================================
DETALHES DO USUÁRIO
================================================================================
ID:                  550e8400-e29b-41d4-a716-446655440000
Email:               usuario@exemplo.com
Username:            user1
Nome Completo:       João Silva
Empresa:             Acme Corp
Cargo:               Desenvolvedor
Bio:                 Desenvolvedor full-stack
Verificado:          ✅ Sim
Ativo:               ✅ Sim
Superusuário:        ❌ Não
OAuth (Google):      N/A
OAuth (GitHub):      N/A
Idiomas que fala:    en, pt
Idiomas que entende: en, pt, es
Criado em:           2025-11-20 10:30:00
Última atualização:  2025-11-26 09:15:00
Último login:        2025-11-26 08:00:00
================================================================================

DADOS RELACIONADOS:
  Perfis de voz:     2
  Salas criadas:     5
  Participações:     12
  Sessões ativas:    1
  API Keys:          0
================================================================================
```

#### 3. Deletar um usuário
```bash
# Por email
python -m backend.admin_users delete usuario@exemplo.com

# Por ID
python -m backend.admin_users delete 550e8400-e29b-41d4-a716-446655440000
```

**Confirmação necessária:**
```
⚠️  Tem certeza que deseja deletar este usuário?
   ID: 550e8400-e29b-41d4-a716-446655440000
   Email: usuario@exemplo.com
   Username: user1
   Nome: João Silva

⚠️  Esta ação é IRREVERSÍVEL!

Digite 'SIM' para confirmar a exclusão: _
```

Após digitar `SIM`:
```
✅ Usuário usuario@exemplo.com deletado com sucesso!
```

---

## 🌐 Via API REST

O backend agora possui endpoints REST para gerenciamento de usuários.

### Autenticação Necessária
Todos os endpoints requerem autenticação via token JWT no header:
```
Authorization: Bearer <seu_token_jwt>
```

### Endpoints Disponíveis

#### 1. Listar todos os usuários
```http
GET /api/admin/users?skip=0&limit=100
```

**Resposta:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "usuario@exemplo.com",
    "username": "user1",
    "full_name": "João Silva",
    "is_active": true,
    "is_verified": true,
    "created_at": "2025-11-20T10:30:00",
    "last_login_at": "2025-11-26T08:00:00"
  }
]
```

#### 2. Ver detalhes de um usuário
```http
GET /api/admin/users/{user_id}
```

**Resposta:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "usuario@exemplo.com",
  "username": "user1",
  "full_name": "João Silva",
  "company": "Acme Corp",
  "job_title": "Desenvolvedor",
  "bio": "Desenvolvedor full-stack",
  "is_active": true,
  "is_verified": true,
  "is_superuser": false,
  "google_id": null,
  "github_id": null,
  "speaks_languages": ["en", "pt"],
  "understands_languages": ["en", "pt", "es"],
  "created_at": "2025-11-20T10:30:00",
  "updated_at": "2025-11-26T09:15:00",
  "last_login_at": "2025-11-26T08:00:00",
  "voice_profiles_count": 2,
  "rooms_count": 5,
  "participations_count": 12
}
```

#### 3. Deletar um usuário
```http
DELETE /api/admin/users/{user_id}
```

**Resposta:**
```json
{
  "message": "User usuario@exemplo.com deleted successfully",
  "deleted_user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 4. Ativar/Desativar usuário
```http
POST /api/admin/users/{user_id}/toggle-active
```

**Resposta:**
```json
{
  "message": "User usuario@exemplo.com is now inactive",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_active": false
}
```

#### 5. Estatísticas do sistema
```http
GET /api/admin/stats
```

**Resposta:**
```json
{
  "total_users": 150,
  "active_users": 145,
  "verified_users": 120,
  "oauth_users": 50,
  "inactive_users": 5,
  "unverified_users": 30
}
```

---

## 🧪 Testando via cURL

### Listar usuários
```bash
curl -X GET "http://localhost:8000/api/admin/users" \
  -H "Authorization: Bearer SEU_TOKEN_JWT"
```

### Ver detalhes de um usuário
```bash
curl -X GET "http://localhost:8000/api/admin/users/{user_id}" \
  -H "Authorization: Bearer SEU_TOKEN_JWT"
```

### Deletar usuário
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/{user_id}" \
  -H "Authorization: Bearer SEU_TOKEN_JWT"
```

### Estatísticas
```bash
curl -X GET "http://localhost:8000/api/admin/stats" \
  -H "Authorization: Bearer SEU_TOKEN_JWT"
```

---

## 📝 Testando via Swagger UI

1. Acesse: `http://localhost:8000/docs`
2. Clique em **Authorize** (cadeado no topo)
3. Cole seu token JWT
4. Navegue até a seção **Admin**
5. Experimente os endpoints diretamente na interface

---

## ⚠️ Notas Importantes

### Segurança
- **ATENÇÃO:** Atualmente qualquer usuário autenticado pode acessar estes endpoints
- Em produção, você deve restringir o acesso apenas para superusuários
- Para adicionar verificação de admin, descomente as linhas no arquivo `backend/api/admin.py`:
  ```python
  if not current_user.is_superuser:
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Not enough permissions"
      )
  ```

### Proteções Implementadas
- ✅ A deleção remove automaticamente todos os dados relacionados (cascade delete)
- ✅ Não é possível deletar sua própria conta via endpoint admin
- ✅ Confirmação obrigatória na CLI antes de deletar
- ✅ Logs de auditoria são mantidos no banco de dados

### Dados que são deletados em cascata:
- Perfis de voz do usuário
- Salas criadas pelo usuário
- Participações em salas
- Sessões ativas
- Chaves de API
- Logs de auditoria do usuário
- Provedores OAuth vinculados

---

## 🔐 Como obter um Token JWT

1. Faça login via API:
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seu@email.com",
    "password": "sua_senha"
  }'
```

2. Na resposta, copie o `access_token`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

3. Use esse token nas requisições admin

---

## 💡 Exemplos Práticos

### Limpar usuários de teste
```bash
# Liste todos os usuários
python -m backend.admin_users list

# Veja detalhes de cada um
python -m backend.admin_users info teste@exemplo.com

# Delete os que não precisa
python -m backend.admin_users delete teste@exemplo.com
```

### Auditoria de usuários inativos
```bash
# Via API - veja as estatísticas
curl -X GET "http://localhost:8000/api/admin/stats" \
  -H "Authorization: Bearer SEU_TOKEN"

# Liste todos para ver quem está inativo
curl -X GET "http://localhost:8000/api/admin/users?limit=1000" \
  -H "Authorization: Bearer SEU_TOKEN" | jq '.[] | select(.is_active==false)'
```

---

## 🆘 Suporte

Se você tiver problemas:

1. Verifique se o backend está rodando: `http://localhost:8000/health`
2. Verifique se o banco de dados está acessível
3. Confirme que você tem permissões adequadas
4. Veja os logs do backend para erros detalhados

---

**Última atualização:** 2025-11-26
