from src.products.schemas import ProductCreateInput, UpdateProductInput
from sqlmodel.ext.asyncio.session import AsyncSession
from src.products.models import Product, ProductSizes
from src.auth.models import User
from sqlmodel import select
from fastapi import HTTPException, status
from sqlalchemy.exc import DatabaseError
import uuid
from sqlalchemy.orm import selectinload
from src.auth.services import AuthServices

authServices = AuthServices()

class ProductServices():

    

    async def create_product(self, product: ProductCreateInput, session: AsyncSession, user_id):
        # Verify the user exists in the system before allowing product creation
        await authServices.check_user_exists(user_id, session)

        # Convert Pydantic model to a dictionary to separate main product data from nested sizes
        product_dict = product.model_dump()
        
        # Remove 'sizes' from the dict so it doesn't crash the Product constructor, 
        # and store them in a temporary list for processing
        sizes_data = product_dict.pop("sizes", [])

        # Initialize the main Product object using the remaining dictionary data (name, base_price, etc.)
        # Still stamp the creator's user_id for now (auditability),
        # but do NOT use it to restrict reads for other company users.
        new_product = Product(**product_dict, user_id=uuid.UUID(user_id))

        # Map the list of size dictionaries into a list of ProductSizes objects.
        # IMPORTANT: We don't pass product_id here manually. By assigning this list to 
        # 'new_product.sizes', SQLModel/SQLAlchemy tracks the relationship and will 
        # automatically inject the correct product_id once the parent is saved.
        new_product.sizes = [ProductSizes(**size) for size in sizes_data]

        # Add the parent object to the session. Because of the relationship mapping, 
        # the nested 'ProductSizes' objects are also added to the session automatically.
        session.add(new_product)

        try:
            # Commit the transaction. The DB inserts the Product first, gets its UUID, 
            # then inserts the ProductSizes using that new UUID as the foreign key.
            await session.commit()
            
            # Reload the object from the database to ensure we have all generated fields (like id and created_at)
            await session.refresh(new_product,["sizes"])
            
            return new_product
        except Exception as e:
            # If anything fails (DB connection, constraint violation), undo all changes 
            # made during this session to keep the data consistent.
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to create product"
            )
        
    async def get_all_products(self, session:AsyncSession, user_id):
        await authServices.check_user_exists(user_id, session)

        statement = select(Product).options(selectinload(Product.sizes))

        try:
            result = await session.exec(statement)
            products = result.all()

            return products
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def get_product_by_id(self, product_id:uuid.UUID, session:AsyncSession, user_id):
        await authServices.check_user_exists(user_id, session)

        statement = select(Product).where(Product.id == product_id).options(selectinload(Product.sizes))

        try:
            result = await session.exec(statement)
            product = result.first()
            return product
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def update_product(self, product_id: uuid.UUID, update_data: UpdateProductInput, session:AsyncSession, user_id):
        await authServices.check_user_exists(user_id, session)

        if update_data.base_price is None and update_data.name is None and update_data.sizes == []:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must provide at least one field to update (name, base_price, sizes)"
            )
        statement = select(Product).where(Product.id == product_id).options(selectinload(Product.sizes))

        try:
            result = await session.exec(statement)
            product = result.first()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Product not found"
                    )
            # Convert the input to a dictionary, excluding unset values
            update_dict = update_data.model_dump(exclude_unset=True)

            new_sizes = update_dict.pop("sizes", None)

            for key, value in update_dict.items():
                setattr(product, key, value)

            if new_sizes is not None:
                # Build a lookup of existing sizes by their name
                existing_by_name = {s.size: s for s in product.sizes}
                updated_sizes = []
                
                for size_data in new_sizes:
                    if size_data["size"] in existing_by_name:
                        # Update existing size's price
                        existing = existing_by_name[size_data["size"]]
                        existing.price = size_data["price"]
                        updated_sizes.append(existing)
                    else:
                        # Create new size
                        updated_sizes.append(ProductSizes(**size_data, product_id=product.id))
                
                # Only keep sizes that are in the new list
                # Note: sizes still referenced by sales will fail to delete - that's expected!
                product.sizes = updated_sizes
            

            await session.commit()
            await session.refresh(product,["sizes"])
            return product
        
        except Exception as e:
            await session.rollback()
            print(f"[UPDATE ERROR] {type(e).__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Update failed: {str(e)}"
            )
        
    async def delete_product(self, product_id:uuid.UUID, session:AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)
        
        statement = select(Product).where(Product.id == product_id)

        try:
            result = await session.exec(statement)
            product = result.first()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found"
                )

            await session.delete(product)
            await session.commit()
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )