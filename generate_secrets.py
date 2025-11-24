#!/usr/bin/env python3
"""
Gerador de variáveis de ambiente seguras para produção do Orbis
Uso: python generate_secrets.py
"""

import secrets
import sys


def generate_secret(length=32):
    """Gera uma chave secreta segura"""
    return secrets.token_urlsafe(length)


def main():
    print("=" * 60)
    print("🔒 ORBIS - Gerador de Secrets para Produção")
    print("=" * 60)
    print()
    print("Copie e cole estas variáveis no Railway/Vercel:")
    print()
    print("-" * 60)
    
    # Database
    print("# DATABASE")
    print(f"POSTGRES_PASSWORD={generate_secret(32)}")
    print()
    
    # Redis
    print("# REDIS")
    print(f"REDIS_PASSWORD={generate_secret(32)}")
    print()
    
    # Security
    print("# SECURITY")
    print(f"SECRET_KEY={generate_secret(32)}")
    print(f"JWT_SECRET={generate_secret(32)}")
    print()
    
    print("-" * 60)
    print()
    print("⚠️  IMPORTANTE:")
    print("  1. Salve estas chaves em local seguro (ex: 1Password)")
    print("  2. NUNCA commite estas chaves no Git")
    print("  3. Use .env.production localmente (gitignored)")
    print("  4. Configure no Railway via dashboard")
    print()
    print("✅ Chaves geradas com sucesso!")
    print()


if __name__ == "__main__":
    main()
