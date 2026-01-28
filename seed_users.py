import asyncio
import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import async_session_maker
from src.auth.models import User, Role
from src.utils.auth import generate_password_hash

async def create_user(username: str, full_name: str, password: str, role: str):
    role_enum = Role.ADMIN if role.lower() == "admin" else Role.STAFF
    
    async with async_session_maker() as session:
        # Check if user already exists
        statement = select(User).where(User.username == username)
        result = await session.exec(statement)
        existing_user = result.first()
        
        if existing_user:
            print(f"Error: User with username '{username}' already exists.")
            return

        new_user = User(
            username=username,
            full_name=full_name,
            password_hash=generate_password_hash(password),
            role=role_enum
        )
        
        session.add(new_user)
        try:
            await session.commit()
            await session.refresh(new_user)
            print(f"Successfully created user!")
            print(f"Username: {new_user.username}")
            print(f"Full Name: {new_user.full_name}")
            print(f"User ID: {new_user.user_id}")
            print(f"Role: {new_user.role}")
            print("-" * 30)
            print("KEEP THIS USER_ID FOR SEEDING PRODUCTS LATER!")
        except Exception as e:
            await session.rollback()
            print(f"Failed to create user: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 5:
        # python seed_users.py <username> <full_name> <password> <role>
        username = sys.argv[1]
        full_name = sys.argv[2]
        password = sys.argv[3]
        role = sys.argv[4]
        asyncio.run(create_user(username, full_name, password, role))
    else:
        print("Usage: python seed_users.py <username> <full_name> <password> <role>")
        print("Example: python seed_users.py admin 'Admin User' mysecretpassword admin")
