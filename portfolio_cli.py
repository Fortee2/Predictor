import argparse
import os
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
import datetime
from dotenv import load_dotenv

class PortfolioCLI:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.portfolio_dao.open_connection()
        self.portfolio_transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.portfolio_transactions_dao.open_connection()
        
    def create_portfolio(self, args):
        portfolio_id = self.portfolio_dao.create_portfolio(args.name, args.description)
        if portfolio_id:
            print(f"Created new portfolio with ID {portfolio_id}")
        else:
            print("Failed to create portfolio")

    def add_tickers(self, args):
        self.portfolio_dao.add_tickers_to_portfolio(args.portfolio_id, args.ticker_ids)

    def remove_tickers(self, args):
        self.portfolio_dao.remove_tickers_from_portfolio(args.portfolio_id, args.ticker_ids)

    def log_transaction(self, args):
        transaction_date = datetime.datetime.strptime(args.transaction_date, '%Y-%m-%d').date()
        portfolio_id = args.portfolio_id
        transaction_type = args.transaction_type
        shares = args.shares
        price = args.price
        amount = args.amount
        
        if transaction_type == 'buy' or transaction_type == 'sell':
            for ticker_id in args.ticker_ids:
                security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
                if security_id:
                    self.portfolio_dao.log_transaction(portfolio_id, security_id, transaction_type, transaction_date, shares, price)
                else:
                    print(f"Ticker {ticker_id} is not associated with portfolio {portfolio_id}. Skipping transaction.")
        elif transaction_type == 'dividend':
            for ticker_id in args.ticker_ids:
                security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
                if security_id:
                    self.portfolio_dao.log_transaction(portfolio_id, security_id, transaction_type, transaction_date, amount=amount)
                else:
                    print(f"Ticker {ticker_id} is not associated with portfolio {portfolio_id}. Skipping transaction.")

    def view_transactions(self, args):
        portfolio_id = args.portfolio_id
        security_id = args.security_id
        
        if security_id:
            transactions = self.portfolio_transactions_dao.get_transaction_history(portfolio_id, security_id)
        else:
            transactions = self.portfolio_transactions_dao.get_transaction_history(portfolio_id)
        
        for transaction in transactions:
            print(transaction)

    def view_portfolio(self, args):
        portfolio_details = self.portfolio_dao.read_portfolio(args.portfolio_id)[0]
        portfolio_id, name, description, active, date_added = portfolio_details
        print(f"Portfolio ID: {portfolio_id}")
        print(f"Name: {name}")
        print(f"Description: {description}")
        print(f"Active: {active}")
        print(f"Date Added: {date_added}")
        tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)
        print("Tickers in Portfolio:")
        for ticker in tickers:
            print(ticker)

    def close_connection(self):
        self.portfolio_dao.close_connection()
        self.portfolio_transactions_dao.close_connection()

def main():
    load_dotenv()
    portfolio_tool = PortfolioCLI(os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME'))
    
    parser = argparse.ArgumentParser(description='Portfolio Management CLI')
    subparsers = parser.add_subparsers(dest='command')

    create_parser = subparsers.add_parser('create-portfolio', help='Create a new portfolio')
    create_parser.add_argument('name', help='Name of the new portfolio')
    create_parser.add_argument('description', help='Description of the new portfolio')

    add_parser = subparsers.add_parser('add-tickers', help='Add tickers to a portfolio')
    add_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    add_parser.add_argument('ticker_ids', nargs='+', type=int, help='Ticker IDs to add')

    remove_parser = subparsers.add_parser('remove-tickers', help='Remove tickers from a portfolio')
    remove_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    remove_parser.add_argument('ticker_ids', nargs='+', type=int, help='Ticker IDs to remove')

    log_parser = subparsers.add_parser('log-transaction', help='Log a transaction for a portfolio')
    log_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    log_parser.add_argument('transaction_type', choices=['buy', 'sell', 'dividend'], help='Transaction type')
    log_parser.add_argument('transaction_date', help='Transaction date (YYYY-MM-DD)')
    log_parser.add_argument('ticker_ids', nargs='+', type=int, help='Ticker IDs for the transaction')
    log_parser.add_argument('--shares', type=int, help='Number of shares (for buy/sell transactions)')
    log_parser.add_argument('--price', type=float, help='Price per share (for buy/sell transactions)')
    log_parser.add_argument('--amount', type=float, help='Amount (for dividend transactions)')

    view_parser = subparsers.add_parser('view-transactions', help='View transaction history for a portfolio')
    view_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    view_parser.add_argument('--security_id', type=int, help='Security ID (optional)')

    view_portfolio_parser = subparsers.add_parser('view-portfolio', help='View details of a portfolio')
    view_portfolio_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')

    args = parser.parse_args()

    if args.command == 'create-portfolio':
        portfolio_tool.create_portfolio(args)
    elif args.command == 'add-tickers':
        portfolio_tool.add_tickers(args)
    elif args.command == 'remove-tickers':
        portfolio_tool.remove_tickers(args)
    elif args.command == 'log-transaction':
        portfolio_tool.log_transaction(args)
    elif args.command == 'view-transactions':
        portfolio_tool.view_transactions(args)
    elif args.command == 'view-portfolio':
        portfolio_tool.view_portfolio(args)
    else:
        parser.print_help()
        
    portfolio_tool.close_connection()

if __name__ == '__main__':
    main()
