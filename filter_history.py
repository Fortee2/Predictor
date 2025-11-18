import csv
from datetime import datetime


def load_transactions():
    transactions = []
    with open("/Users/randycostner/Desktop/transactions.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert date string to datetime
            date = datetime.strptime(row["transaction_date"], "%Y-%m-%d")
            # Handle NULL values in shares and price
            shares = float(row["shares"]) if row["shares"] and row["shares"] != "NULL" else 0
            price = float(row["price"]) if row["price"] and row["price"] != "NULL" else 0
            transactions.append(
                {
                    "date": date,
                    "ticker": row["ticker"],
                    "type": row["transaction_type"],
                    "shares": shares,
                    "price": price,
                }
            )
    return transactions


def load_and_filter_history():
    try:
        transactions = load_transactions()
        filtered_history = []

        history_path = "/Users/randycostner/Downloads/History_for_Account_211749109 (1).csv"
        output_path = "/Volumes/Seagate Portabl/Projects/Predictor/filtered_history.csv"

        print(f"Reading history from: {history_path}")
        with open(history_path, "r", encoding="utf-8-sig") as f:
            # Read all lines and filter out empty lines and footer
            lines = [line for line in f if line.strip() and not line.startswith('"The data')]

            # Create reader with the filtered lines
            reader = csv.DictReader(lines)
            header = reader.fieldnames

            for row in reader:
                try:
                    # Convert date string to datetime
                    date = datetime.strptime(row["Run Date"], "%m/%d/%Y")

                    # Extract transaction type
                    hist_type = (
                        "buy" if "YOU BOUGHT" in row["Action"] else "sell" if "YOU SOLD" in row["Action"] else "other"
                    )

                    # Skip if not a buy/sell transaction
                    if hist_type == "other":
                        filtered_history.append(row)
                        continue

                    # Extract quantity and price
                    quantity = float(row["Quantity"]) if row["Quantity"] else 0
                    price = float(row["Price ($)"]) if row["Price ($)"] else 0

                    # Check if this history entry matches any transaction
                    found_match = False
                    for trans in transactions:
                        if (
                            trans["date"].date() == date.date()
                            and trans["ticker"] == row["Symbol"]
                            and trans["type"] == hist_type
                            and abs(trans["shares"] - abs(quantity)) < 0.01  # Use small threshold for float comparison
                            and (price == 0 or abs(trans["price"] - price) < 0.01)
                        ):  # Some prices might be 0 in transactions
                            found_match = True
                            break

                    if not found_match:
                        filtered_history.append(row)
                except Exception as e:
                    print(f"Warning: Skipping row due to error: {str(e)}")
                    print(f"Row content: {row}")
                    continue

        # Write filtered history to new CSV
        if filtered_history:
            print(f"Writing filtered history to: {output_path}")
            with open(output_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(filtered_history)
            print(f"Successfully wrote {len(filtered_history)} entries to filtered history")
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Current row being processed: {row if 'row' in locals() else 'No row information available'}")


if __name__ == "__main__":
    load_and_filter_history()
