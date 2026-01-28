from src.sales.schemas import SaleInput
from sqlmodel.ext.asyncio.session import AsyncSession
from src.sales.models import Sale, SaleItem, SaleStatus
from src.products.models import Product, ProductSizes
from src.customers.models import Customer
from sqlmodel import select
from fastapi import HTTPException, status
from sqlalchemy.exc import DatabaseError
import uuid
from sqlalchemy.orm import selectinload
from decimal import Decimal
from src.auth.services import AuthServices
from src.payments.models import Payment, SalePaymentLink
authServices = AuthServices()

class SaleServices:

    async def create_sale(self, sale: SaleInput, session: AsyncSession, user_id):
        await authServices.check_user_exists(user_id, session)

        user_uuid = uuid.UUID(user_id)
        sale_dict = sale.model_dump()

        sale_items = sale_dict.pop("items", [])
        
        # Capture the raw payment amount before we manipulate the sale_dict
        upfront_payment = sale_dict.get("amount_paid", Decimal("0.0"))

        sale_items_calculated = []
        total_amount = Decimal("0.0")
        
        product_ids = [item["product_id"] for item in sale_items]

        # Company-wide access: do not restrict products by user_id (for now)
        product_statement = select(Product).where(Product.id.in_(product_ids))
        result = await session.exec(product_statement)

        products_map = {p.id: p for p in result.all()}

        for p_id in product_ids:
            if p_id not in products_map:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Product {p_id} is invalid. Sale cancelled."
                )
            
        for item in sale_items:
            product = products_map[item["product_id"]]
            size_id = item.get("size_id")
            
            unit_price = product.base_price
            
            if size_id:
                # Fetch specific size price
                size_statement = select(ProductSizes).where(
                    ProductSizes.id == size_id, 
                    ProductSizes.product_id == product.id
                )
                size_result = await session.exec(size_statement)
                product_size = size_result.first()
                if not product_size:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Size {size_id} for product {product.id} not found."
                    )
                unit_price = product_size.price

            item["unit_price"] = unit_price
            item_total = Decimal(str(item["quantity"])) * unit_price
            item["total"] = item_total
            total_amount += item_total

            sale_items_calculated.append(item)
        
        sale_dict["total_amount"] = total_amount
        # Still stamp the creator's user_id for auditability (not used for read restrictions)
        sale_dict["user_id"] = user_uuid

        # Use with_for_update() to prevent race conditions on balance updates
        # Company-wide access: do not restrict customers by user_id (for now)
        customer_statement = select(Customer).where(Customer.id == sale_dict["customer_id"]).with_for_update()
        customer_result = await session.exec(customer_statement)
        customer = customer_result.first()

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="customer not found"
            )
        
        # Calculate effective payment: upfront payment + any existing credit balance
        effective_payment = upfront_payment + customer.credit_balance
        
        # Calculate how much can be applied to THIS sale
        amount_applied_to_sale = min(effective_payment, total_amount)
        credit_used_for_sale = max(Decimal("0.0"), amount_applied_to_sale - upfront_payment)
        
        # Calculate Status based on effective payment (upfront + credit)
        if amount_applied_to_sale >= total_amount:
            sale_dict["status"] = SaleStatus.FULLY_PAID
            sale_dict["amount_paid"] = total_amount
        elif amount_applied_to_sale > 0:
            sale_dict["status"] = SaleStatus.PARTIALLY_PAID
            sale_dict["amount_paid"] = amount_applied_to_sale
        else:
            sale_dict["status"] = SaleStatus.UNPAID
            sale_dict["amount_paid"] = Decimal("0.0")
        
        # Store how much credit was applied to this sale
        sale_dict["credit_applied"] = credit_used_for_sale

        # Update global balances
        # Remaining effective payment after paying this sale
        remaining_effective = effective_payment - amount_applied_to_sale
        
        # Debt from this sale (if any)
        new_debt_from_sale = total_amount - amount_applied_to_sale
        
        if remaining_effective > 0:
            # They have leftover after paying this sale
            if customer.total_debt > 0:
                # Apply remaining to existing debt
                if remaining_effective >= customer.total_debt:
                    leftover_credit = remaining_effective - customer.total_debt
                    customer.total_debt = Decimal("0.0")
                    customer.credit_balance = leftover_credit
                else:
                    customer.total_debt -= remaining_effective
                    customer.credit_balance = Decimal("0.0")
            else:
                customer.credit_balance = remaining_effective
        else:
            # No remaining effective payment
            customer.credit_balance = Decimal("0.0")
            customer.total_debt += new_debt_from_sale

        #Create Sale Instance
        new_sale = Sale(**sale_dict)
        new_sale.items = [SaleItem(**item) for item in sale_items_calculated]
        session.add(new_sale)

        #Handle Upfront Payment & Audit Trail
        if upfront_payment > 0:
            # Create a formal payment record for the cash payment
            new_payment = Payment(
                customer_id=customer.id,
                user_id=user_uuid,
                amount=upfront_payment,
                payment_type=sale.payment_type
            )
            session.add(new_payment)

            await session.flush() 

            # Link the upfront payment portion to this sale
            applied_from_upfront = min(upfront_payment, total_amount)

            new_link = SalePaymentLink(
                sale_id=new_sale.id,
                payment_id=new_payment.id,
                amount_applied=applied_from_upfront
            )
            session.add(new_link)
        
        # If credit was used, we need to flush to get sale ID for linking
        if credit_used_for_sale > 0 and upfront_payment == 0:
            await session.flush()

        try:
            await session.commit()
            await session.refresh(new_sale, ["items"])
            return new_sale
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to create sale"
            )
        
    async def get_all_sales(self, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        statement = select(Sale).options(selectinload(Sale.items))

        try:
            result = await session.exec(statement)
            sales = result.all()

            return sales
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        

        
    async def get_sale_by_id(self, sale_id: uuid.UUID, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        statement = select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.items))

        try:
            result = await session.exec(statement)
            sale = result.first()

            if not sale:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sale not found"
                )

            return sale
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        
    