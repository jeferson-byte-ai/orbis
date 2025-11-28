"""
Admin utility to manage users in the Orbis database
Usage:
    python -m backend.admin_users list           # List all users
    python -m backend.admin_users delete <email> # Delete user by email
    python -m backend.admin_users delete <user_id> # Delete user by ID
"""
import sys
import asyncio
from sqlalchemy import select
from backend.db.session import get_db
from backend.db.models import User

def list_users():
    """List all registered users"""
    db = next(get_db())
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("❌ Nenhum usuário cadastrado no sistema.")
            return
        
        print(f"\n✅ Total de usuários cadastrados: {len(users)}\n")
        print("=" * 120)
        print(f"{'ID':<38} {'Email':<30} {'Username':<20} {'Nome Completo':<20} {'Criado em':<20}")
        print("=" * 120)
        
        for user in users:
            created_at = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
            full_name = user.full_name or "N/A"
            print(f"{str(user.id):<38} {user.email:<30} {user.username:<20} {full_name:<20} {created_at:<20}")
        
        print("=" * 120)
        
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")
    finally:
        db.close()


def delete_user(identifier: str):
    """Delete a user by email or ID"""
    db = next(get_db())
    
    try:
        # Try to find user by email first
        user = db.query(User).filter(User.email == identifier).first()
        
        # If not found by email, try by ID
        if not user:
            user = db.query(User).filter(User.id == identifier).first()
        
        if not user:
            print(f"❌ Usuário não encontrado: {identifier}")
            return
        
        # Show user info and ask for confirmation
        print(f"\n⚠️  Tem certeza que deseja deletar este usuário?")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   Nome: {user.full_name or 'N/A'}")
        print(f"\n⚠️  Esta ação é IRREVERSÍVEL!\n")
        
        confirm = input("Digite 'SIM' para confirmar a exclusão: ")
        
        if confirm.strip().upper() != "SIM":
            print("❌ Operação cancelada.")
            return
        
        # Delete the user (cascades will handle related data)
        db.delete(user)
        db.commit()
        
        print(f"✅ Usuário {user.email} deletado com sucesso!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao deletar usuário: {e}")
    finally:
        db.close()


def show_user_details(identifier: str):
    """Show detailed information about a user"""
    db = next(get_db())
    
    try:
        # Try to find user by email first
        user = db.query(User).filter(User.email == identifier).first()
        
        # If not found by email, try by ID
        if not user:
            user = db.query(User).filter(User.id == identifier).first()
        
        if not user:
            print(f"❌ Usuário não encontrado: {identifier}")
            return
        
        print(f"\n{'='*80}")
        print(f"DETALHES DO USUÁRIO")
        print(f"{'='*80}")
        print(f"ID:                  {user.id}")
        print(f"Email:               {user.email}")
        print(f"Username:            {user.username}")
        print(f"Nome Completo:       {user.full_name or 'N/A'}")
        print(f"Empresa:             {user.company or 'N/A'}")
        print(f"Cargo:               {user.job_title or 'N/A'}")
        print(f"Bio:                 {user.bio or 'N/A'}")
        print(f"Verificado:          {'✅ Sim' if user.is_verified else '❌ Não'}")
        print(f"Ativo:               {'✅ Sim' if user.is_active else '❌ Não'}")
        print(f"Superusuário:        {'✅ Sim' if user.is_superuser else '❌ Não'}")
        print(f"OAuth (Google):      {user.google_id or 'N/A'}")
        print(f"OAuth (GitHub):      {user.github_id or 'N/A'}")
        print(f"Idiomas que fala:    {', '.join(user.speaks_languages or ['N/A'])}")
        print(f"Idiomas que entende: {', '.join(user.understands_languages or ['N/A'])}")
        print(f"Criado em:           {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}")
        print(f"Última atualização:  {user.updated_at.strftime('%Y-%m-%d %H:%M:%S') if user.updated_at else 'N/A'}")
        print(f"Último login:        {user.last_login_at.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_at else 'N/A'}")
        print(f"{'='*80}\n")
        
        # Show related data counts
        print(f"DADOS RELACIONADOS:")
        print(f"  Perfis de voz:     {len(user.voice_profiles)}")
        print(f"  Salas criadas:     {len(user.created_rooms)}")
        print(f"  Participações:     {len(user.room_participations)}")
        print(f"  Sessões ativas:    {len([s for s in user.sessions if s.is_active])}")
        print(f"  API Keys:          {len([k for k in user.api_keys if k.is_active])}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Erro ao buscar detalhes do usuário: {e}")
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_users()
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Erro: Forneça o email ou ID do usuário para deletar")
            print("   Exemplo: python -m backend.admin_users delete usuario@exemplo.com")
            return
        delete_user(sys.argv[2])
    elif command == "info" or command == "show":
        if len(sys.argv) < 3:
            print("❌ Erro: Forneça o email ou ID do usuário")
            print("   Exemplo: python -m backend.admin_users info usuario@exemplo.com")
            return
        show_user_details(sys.argv[2])
    else:
        print(f"❌ Comando desconhecido: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
