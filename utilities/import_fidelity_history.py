import csv
import datetime

from portfolio_cli import PortfolioCLI  # Assuming portfolio_cli.py is in the same directory


def import_transactions_from_csv(portfolio_id, csv_filepath):
    """
    Reads transactions from a CSV file and logs them to the portfolio tool.

    Args:
        portfolio_id (int): The ID of the portfolio to log transactions to.
        csv_filepath (str): The path to the CSV file containing transaction history.
    """
    cli = PortfolioCLI()

    # Counter for successful imports
    successful_imports = 0
    total_transactions = 0

    try:
        with open(csv_filepath, mode="r", encoding="utf-8") as file:
            # Skip initial descriptive lines until the header row is found
            reader = csv.reader(file)
            header_found = False
            header = []
            transaction_data = []

            for row in reader:
                # Filter out empty rows
                if not any(cell.strip() for cell in row):
                    continue

                # Check if this is the header row based on expected content
                if "Run Date" in row and "Symbol" in row and "Amount ($)" in row:
                    header = row
                    header_found = True
                    continue

                if header_found:
                    transaction_data.append(row)

            if not header_found:
                print("Error: Could not find the expected header row in the CSV.")
                return

            # Map header names to their column indices
            col_map = {h.strip(): i for i, h in enumerate(header)}

            # Verify essential columns exist
            required_cols = [
                "Run Date",
                "Action",
                "Symbol",
                "Quantity",
                "Price ($)",
                "Amount ($)",
                "Type",
            ]
            if not all(col in col_map for col in required_cols):
                print(f"Error: Missing one or more required columns in CSV. Expected: {required_cols}")
                return

            # Process transactions in reverse order to simulate chronological logging
            # (oldest transaction first, which is better for cash balance tracking)
            for row in reversed(transaction_data):
                total_transactions += 1
                try:
                    account = (
                        row[col_map["Account"]].strip()
                        if "Account" in col_map and row[col_map["Account"]]
                        else "Rollover IRA"
                    )
                    action = row[col_map["Action"]].strip()

                    if account != "Rollover IRA" or "REINVESTMENT FIDELITY GOVERNMENT MONEY MARKET (SPAXX)" in action:
                        print(f"Skipping transaction for unsupported account '{account}' or action '{action}'.")
                        continue

                    if "DIVIDEND RECEIVED FIDELITY GOVERNMENT MONEY MARKET (SPAXX)" in action:
                        action = "CASH CONTRIBUTION"

                    date_str = row[col_map["Run Date"]].strip()
                    symbol = row[col_map["Symbol"]].strip() if "Symbol" in col_map and row[col_map["Symbol"]] else None
                    quantity_str = row[col_map["Quantity"]].strip()
                    price_str = row[col_map["Price ($)"]].strip()
                    amount_str = row[col_map["Amount ($)"]].strip()
                    transaction_type_csv = row[col_map["Type"]].strip()  # 'Cash' or something else

                    # Clean and convert data
                    shares = float(quantity_str) if quantity_str and quantity_str != "0.000" else None
                    price = float(price_str) if price_str else None
                    amount = float(amount_str) if amount_str else None

                    # Determine transaction type for CLI and adjust parameters
                    cli_transaction_type = None
                    log_shares = shares
                    log_price = price
                    log_amount = amount  # Default, might be adjusted

                    date_object = datetime.datetime.strptime(date_str, "%m/%d/%Y").date()

                    if "YOU BOUGHT" in action:
                        cli_transaction_type = "buy"
                        # For 'buy' from CSV, the amount is negative. The log_transaction handles the cash reduction.
                        # Shares and price are paramount for buy/sell.
                        if shares is None or price is None:
                            print(f"Skipping row (missing shares/price for buy): {row}")
                            continue
                        log_amount = None  # Ensure amount is None for buy/sell
                    elif "YOU SOLD" in action:
                        cli_transaction_type = "sell"
                        # For 'sell' from CSV, shares are negative. Make them positive for logging.
                        log_shares = abs(shares)
                        if shares is None or price is None:
                            print(f"Skipping row (missing shares/price for sell): {row}")
                            continue
                        log_amount = None  # Ensure amount is None for buy/sell
                    elif "DIVIDEND RECEIVED" in action:
                        cli_transaction_type = "dividend"
                        if amount is None:
                            print(f"Skipping row (missing amount for dividend): {row}")
                            continue
                        log_shares = None
                        log_price = None
                    elif "CASH CONTRIBUTION" in action:
                        # SPAXX is the cash holding security in Fidelity accounts.
                        # It pays interest which is treated as a dividend.
                        cli_transaction_type = "cash"
                        if amount is None:
                            print(f"Skipping row (missing amount for cash contribution): {row}")
                            continue
                        # Amount is positive for cash contributions as per your CSV
                        log_shares = None
                        log_price = None
                        log_amount = amount
                    elif "REINVESTMENT" in action:
                        # REINVESTMENT is a 'buy' operation.
                        # It implicitly uses the dividend amount to buy shares.
                        cli_transaction_type = "buy"
                        if shares is None or price is None:
                            print(f"Skipping row (missing shares/price for reinvestment buy): {row}")
                            continue
                        log_amount = None  # Ensure amount is None for buy/sell

                    else:
                        print(f"Warning: Unrecognized action type '{action}'. Skipping row: {row}")
                        continue

                    print(f"Processing: {action} on {date_str} for {symbol if symbol else 'Cash'}")
                    cli.log_transaction(
                        portfolio_id=portfolio_id,
                        transaction_type=cli_transaction_type,
                        date_str=date_object.isoformat(),
                        ticker_symbol=symbol,
                        shares=log_shares,
                        price=log_price,
                        amount=log_amount,
                    )
                    successful_imports += 1

                except ValueError as ve:
                    print(f"Data conversion error in row: {row}. Error: {ve}. Skipping.")
                except IndexError as ie:
                    print(
                        f"Column index error in row: {row}. Ensure all expected columns are present. Error: {ie}. Skipping."
                    )
                except Exception as e:
                    print(f"An unexpected error occurred processing row: {row}. Error: {e}. Skipping.")

    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cli.portfolio_dao.close_connection()
        cli.transactions_dao.close_connection()
        cli.ticker_dao.close_connection()
        cli.rsi_calc.close_connection()
        cli.moving_avg.close_connection()
        cli.fundamental_dao.close_connection()
        cli.value_calculator.close_connection()
        cli.macd_analyzer.close_connection()
        cli.trend_analyzer.close_connection()
        cli.watch_list_dao.close_connection()

        print("\n--- Transaction Import Summary ---")
        print(f"Total rows processed from CSV (excluding header and blank rows): {total_transactions}")
        print(f"Successfully imported transactions: {successful_imports}")
        print(f"Transactions skipped due to errors: {total_transactions - successful_imports}")


if __name__ == "__main__":
    # --- Configuration ---
    # IMPORTANT: Replace with your actual portfolio ID
    target_portfolio_id = 1

    # IMPORTANT: Replace with the actual path to your Accounts_History.csv file
    csv_file_path = "Accounts_History_2024.csv"

    print(f"Starting import of transactions from '{csv_file_path}' into Portfolio ID: {target_portfolio_id}")
    import_transactions_from_csv(target_portfolio_id, csv_file_path)
    print("\nImport process finished.")
    print(
        "Consider running 'python portfolio_cli.py recalculate-history <portfolio_id>' after import to update historical values."
    )
