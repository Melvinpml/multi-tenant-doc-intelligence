"""
Database Verification Script
Place this file in the project root (same directory as main.py)
Run with: python check_db.py
"""

import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.core.config import settings

async def check_database():
    print("\n" + "=" * 50)
    print("🔍 DATABASE VERIFICATION")
    print("=" * 50)
    print(f"📡 Database: {settings.DATABASE_URL}\n")
    
    try:
        async with AsyncSessionLocal() as db:
            # Check if we can connect
            result = await db.execute(text("SELECT version()"))
            version = result.scalar()
            print("✅ Database connection successful!")
            print(f"   PostgreSQL version: {version.split(',')[0]}\n")
            
            # List all tables
            result = await db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = result.fetchall()
            
            print("📊 All tables in database:")
            if tables:
                for table in tables:
                    print(f"   ✓ {table[0]}")
            else:
                print("   ⚠️ No tables found!")
            
            print("\n" + "-" * 50)
            
            # Check our expected tables
            expected_tables = ['users', 'companies', 'company_members']
            print("🎯 Authentication tables:")
            for expected in expected_tables:
                exists = any(table[0] == expected for table in tables)
                icon = "✅" if exists else "❌"
                print(f"   {icon} {expected}")
            
            # Check PostgreSQL enum type
            result = await db.execute(text("""
                SELECT typname 
                FROM pg_type 
                WHERE typname = 'roleenum';
            """))
            role_enum = result.fetchone()
            print(f"\n📝 RoleEnum type: {'✅ Exists' if role_enum else '❌ Missing'}")
            
            # Show row counts
            print("\n📈 Record counts:")
            for table in expected_tables:
                if any(t[0] == table for t in tables):
                    result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"   {table}: {count} rows")
            
            # Show users if any exist
            if any(t[0] == 'users' for t in tables):
                result = await db.execute(text("SELECT email, is_active FROM users LIMIT 5"))
                users = result.fetchall()
                if users:
                    print("\n👥 Sample users:")
                    for user in users:
                        status = "active" if user[1] else "inactive"
                        print(f"   - {user[0]} ({status})")
            
            print("\n" + "=" * 50)
            print("✅ Database verification complete!")
            print("=" * 50 + "\n")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. PostgreSQL is running")
        print("2. DATABASE_URL is correct in .env file")
        print("3. Database exists and is accessible")

if __name__ == "__main__":
    asyncio.run(check_database())