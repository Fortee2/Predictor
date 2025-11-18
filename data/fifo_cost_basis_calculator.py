"""
FIFO Cost Basis Calculator

This module provides a First-In-First-Out (FIFO) cost basis calculation system
for portfolio management. FIFO is the most commonly used method for tax reporting
and provides accurate tracking of realized and unrealized gains/losses.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List


class FIFOLot:
    """Represents a single lot of shares purchased at a specific price and date."""

    def __init__(self, shares: float, price: float, purchase_date: date):
        self.shares = Decimal(str(shares)).quantize(Decimal("0.0001"))
        self.price = Decimal(str(price)).quantize(Decimal("0.01"))
        self.purchase_date = purchase_date
        self.original_shares = self.shares

    @property
    def cost_basis(self) -> Decimal:
        """Total cost basis for this lot."""
        return self.shares * self.price

    def __repr__(self):
        return f"FIFOLot({self.shares} shares @ ${self.price} on {self.purchase_date})"


class FIFOCostBasisCalculator:
    """
    FIFO (First-In-First-Out) cost basis calculator.

    This calculator maintains a queue of purchase lots and processes sales
    by removing shares from the oldest lots first, providing accurate
    cost basis tracking for tax reporting and performance analysis.
    """

    def __init__(self):
        self.lots: List[FIFOLot] = []
        self.realized_gains: List[Dict[str, Any]] = []

    def add_purchase(self, shares: float, price: float, purchase_date: date) -> None:
        """
        Add a purchase transaction (buy).

        Args:
            shares (float): Number of shares purchased
            price (float): Price per share
            purchase_date (date): Date of purchase
        """
        if shares <= 0 or price < 0:
            raise ValueError("Shares must be greater than 0 and price must be positive")

        lot = FIFOLot(shares, price, purchase_date)
        self.lots.append(lot)

    def process_sale(self, shares_to_sell: float, sale_price: float, sale_date: date) -> Dict[str, Any]:
        """
        Process a sale transaction using FIFO method.

        Args:
            shares_to_sell (float): Number of shares to sell
            sale_price (float): Price per share for the sale
            sale_date (date): Date of sale

        Returns:
            Dict containing:
                - shares_sold (Decimal): Actual shares sold
                - total_proceeds (Decimal): Total sale proceeds
                - total_cost_basis (Decimal): Total cost basis of sold shares
                - realized_gain_loss (Decimal): Realized gain/loss
                - lots_used (List): Details of lots used for the sale
                - remaining_shares (Decimal): Shares remaining after sale
        """
        if shares_to_sell <= 0 or sale_price <= 0:
            raise ValueError("Shares to sell and sale price must be positive")

        shares_remaining_to_sell = Decimal(str(shares_to_sell)).quantize(Decimal("0.0001"))
        sale_price_decimal = Decimal(str(sale_price)).quantize(Decimal("0.01"))

        total_proceeds = Decimal("0")
        total_cost_basis = Decimal("0")
        lots_used = []
        shares_actually_sold = Decimal("0")

        # Process sale using FIFO method
        while shares_remaining_to_sell > 0 and self.lots:
            current_lot = self.lots[0]

            if current_lot.shares <= shares_remaining_to_sell:
                # Use entire lot
                shares_from_lot = current_lot.shares
                cost_basis_from_lot = current_lot.cost_basis

                # Remove the lot entirely
                self.lots.pop(0)
            else:
                # Use partial lot
                shares_from_lot = shares_remaining_to_sell
                cost_basis_from_lot = shares_from_lot * current_lot.price

                # Reduce the lot size
                current_lot.shares -= shares_from_lot

            # Calculate proceeds and track the lot used
            proceeds_from_lot = shares_from_lot * sale_price_decimal
            gain_loss_from_lot = proceeds_from_lot - cost_basis_from_lot

            lots_used.append(
                {
                    "shares": float(shares_from_lot),
                    "purchase_price": float(current_lot.price),
                    "purchase_date": current_lot.purchase_date,
                    "cost_basis": float(cost_basis_from_lot),
                    "proceeds": float(proceeds_from_lot),
                    "gain_loss": float(gain_loss_from_lot),
                }
            )

            total_proceeds += proceeds_from_lot
            total_cost_basis += cost_basis_from_lot
            shares_actually_sold += shares_from_lot
            shares_remaining_to_sell -= shares_from_lot

        # Calculate total realized gain/loss
        realized_gain_loss = total_proceeds - total_cost_basis

        # Record the realized gain/loss
        gain_loss_record = {
            "sale_date": sale_date,
            "shares_sold": float(shares_actually_sold),
            "sale_price": float(sale_price_decimal),
            "total_proceeds": float(total_proceeds),
            "total_cost_basis": float(total_cost_basis),
            "realized_gain_loss": float(realized_gain_loss),
            "lots_used": lots_used,
        }
        self.realized_gains.append(gain_loss_record)

        return {
            "shares_sold": shares_actually_sold,
            "total_proceeds": total_proceeds,
            "total_cost_basis": total_cost_basis,
            "realized_gain_loss": realized_gain_loss,
            "lots_used": lots_used,
            "remaining_shares": self.get_total_shares(),
            "oversold_shares": (float(shares_remaining_to_sell) if shares_remaining_to_sell > 0 else 0),
        }

    def get_total_shares(self) -> Decimal:
        """Get total shares currently held."""
        return sum(lot.shares for lot in self.lots)

    def get_total_cost_basis(self) -> Decimal:
        """Get total cost basis of all held shares."""
        return sum(lot.cost_basis for lot in self.lots)

    def get_average_cost_per_share(self) -> Decimal:
        """Get average cost per share of all held shares."""
        total_shares = self.get_total_shares()
        if total_shares > 0:
            return (self.get_total_cost_basis() / total_shares).quantize(Decimal("0.01"))
        return Decimal("0")

    def get_unrealized_gain_loss(self, current_price: float) -> Dict[str, Any]:
        """
        Calculate unrealized gain/loss based on current market price.

        Args:
            current_price (float): Current market price per share

        Returns:
            Dict containing unrealized gain/loss details
        """
        current_price_decimal = Decimal(str(current_price)).quantize(Decimal("0.01"))
        total_shares = self.get_total_shares()
        total_cost_basis = self.get_total_cost_basis()
        current_market_value = total_shares * current_price_decimal
        unrealized_gain_loss = current_market_value - total_cost_basis

        return {
            "total_shares": float(total_shares),
            "average_cost_per_share": float(self.get_average_cost_per_share()),
            "total_cost_basis": float(total_cost_basis),
            "current_price": float(current_price_decimal),
            "current_market_value": float(current_market_value),
            "unrealized_gain_loss": float(unrealized_gain_loss),
            "unrealized_gain_loss_pct": (
                float((unrealized_gain_loss / total_cost_basis * 100)) if total_cost_basis > 0 else 0
            ),
        }

    def get_position_summary(self, current_price: float = None) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the current position.

        Args:
            current_price (float, optional): Current market price for unrealized calculations

        Returns:
            Dict containing complete position summary
        """
        total_shares = self.get_total_shares()
        total_cost_basis = self.get_total_cost_basis()
        avg_cost = self.get_average_cost_per_share()

        summary = {
            "total_shares": float(total_shares),
            "total_cost_basis": float(total_cost_basis),
            "average_cost_per_share": float(avg_cost),
            "number_of_lots": len(self.lots),
            "realized_transactions": len(self.realized_gains),
            "total_realized_gain_loss": sum(rg["realized_gain_loss"] for rg in self.realized_gains),
        }

        if current_price is not None:
            unrealized = self.get_unrealized_gain_loss(current_price)
            summary.update(unrealized)

        return summary

    def get_lot_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about all current lots."""
        return [
            {
                "shares": float(lot.shares),
                "price": float(lot.price),
                "purchase_date": lot.purchase_date,
                "cost_basis": float(lot.cost_basis),
                "original_shares": float(lot.original_shares),
            }
            for lot in self.lots
        ]

    def get_realized_gains_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all realized gains/losses."""
        return self.realized_gains.copy()

    def clear_position(self) -> None:
        """Clear all lots and realized gains (use with caution)."""
        self.lots.clear()
        self.realized_gains.clear()


def calculate_fifo_position_from_transactions(
    transactions: List[Dict[str, Any]],
) -> FIFOCostBasisCalculator:
    """
    Create a FIFO calculator from a list of transactions.

    Args:
        transactions (List[Dict]): List of transaction dictionaries with keys:
            - transaction_type: 'buy' or 'sell'
            - transaction_date: date object
            - shares: number of shares
            - price: price per share

    Returns:
        FIFOCostBasisCalculator: Calculator with all transactions processed
    """
    calculator = FIFOCostBasisCalculator()

    # Sort transactions by date to ensure proper chronological processing
    sorted_transactions = sorted(transactions, key=lambda x: (x["transaction_date"], x.get("id", 0)))

    for transaction in sorted_transactions:
        trans_type = transaction["transaction_type"]
        trans_date = transaction["transaction_date"]
        shares = float(transaction["shares"] or 0)
        price = float(transaction["price"] or 0)

        if shares <= 0 or price <= 0:
            continue

        try:
            if trans_type in ("buy", "split_adjustment"):
                calculator.add_purchase(shares, price, trans_date)
            elif trans_type == "sell":
                calculator.process_sale(shares, price, trans_date)
        except ValueError as e:
            print(f"Warning: Skipping invalid transaction: {e}")
            continue

    return calculator
