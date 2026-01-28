import asyncio
import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import async_session_maker
from src.products.models import Product, ProductSizes, Category
from src.products.extracted_prices import PRINTING_PRICES, BORDERLESS_BOARD_PRICES, FRAME_PRICES, MISC_PRICES

# IMPORTANT: SET THE USER_ID TO THE ACCOUNT YOU WANT TO SEED
TARGET_USER_ID = "a407106f-0a5c-4444-a3f7-e211bd077a9d"

async def seed_data():
    if TARGET_USER_ID == "YOUR_USER_ID_HERE":
        print("Error: Please set TARGET_USER_ID in the script or pass it as an argument!")
        return

    async with async_session_maker() as session:
        user_uuid = uuid.UUID(TARGET_USER_ID)

        # 1. Create Photo Printing Product (Category: PRINTING)
        photo_printing = Product(
            name="Photo Printing",
            base_price=250.00,
            category=Category.PRINTING,
            user_id=user_uuid
        )
        photo_printing.sizes = [ProductSizes(size=item["size"], price=item["price"]) for item in PRINTING_PRICES]
        session.add(photo_printing)

        # 2. Create Borderless Board Product (Category: MATERIALS)
        borderless_board = Product(
            name="Borderless Board",
            base_price=300.00,
            category=Category.MATERIALS,
            user_id=user_uuid
        )
        borderless_board.sizes = [ProductSizes(size=item["size"], price=item["price"]) for item in BORDERLESS_BOARD_PRICES]
        session.add(borderless_board)

        # 3. Create Picture Frames Product (Category: MATERIALS)
        picture_frames = Product(
            name="Picture Frames",
            base_price=2200.00,
            category=Category.MATERIALS,
            user_id=user_uuid
        )
        frame_sizes = []
        for item in FRAME_PRICES:
            if item["tiny"]:
                frame_sizes.append(ProductSizes(size=f"{item['size']} Tiny", price=item["tiny"]))
            if item["versace"]:
                frame_sizes.append(ProductSizes(size=f"{item['size']} Versace", price=item["versace"]))
            if item["normal"]:
                frame_sizes.append(ProductSizes(size=f"{item['size']} Normal", price=item["normal"]))
        
        picture_frames.sizes = frame_sizes
        session.add(picture_frames)

        # 4. Create Miscellaneous Products (Grouped by Name)
        grouped_misc = {}
        for item in MISC_PRICES:
            name = item["name"]
            if name not in grouped_misc:
                grouped_misc[name] = []
            grouped_misc[name].append(item)

        for name, items in grouped_misc.items():
            base_price = min(item["price"] for item in items)
            product = Product(
                name=name,
                base_price=base_price,
                category=Category.BANNER if name == "Banner" else (Category.PRINTING if name == "Sticker" else Category.MATERIALS),
                user_id=user_uuid
            )
            product.sizes = [ProductSizes(size=item["size"], price=item["price"]) for item in items]
            session.add(product)

        # Strip timezone from created_at for ALL new objects to match your naive DB columns
        for obj in session.new:
            if hasattr(obj, 'created_at') and obj.created_at:
                obj.created_at = obj.created_at.replace(tzinfo=None)

        try:
            await session.commit()
            print(f"Successfully seeded products for user {TARGET_USER_ID}")
        except Exception as e:
            await session.rollback()
            print(f"Failed to seed data: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        TARGET_USER_ID = sys.argv[1]
    
    asyncio.run(seed_data())
