# Stock Trading with Q-Learning

This project demonstrates how to use Q-learning to build a simple stock trading model. The model aims to maximize the total reward by deciding when to buy, sell, or hold a stock.  This project is for educational purposes only.

## Dependencies

- numpy
- pandas
- scikit-learn
- gym

You can install these dependencies using pip:

```bash
pip install numpy pandas scikit-learn gym
```

## Data
This project expects a CSV file with the following columns:

- date
- close (closing price of the stock)
- volume

Example: ford_activity.csv

```
date,close,volume
2018-01-02,12.00,12345678
2018-01-03,12.50,23456789
...
```

## Usage
Clone this repository:
``` bash
git clone https://github.com/your_username/stock_trading_q_learning.git
cd stock_trading_q_learning
```

Replace ford_activity.csv with your own stock data file or use the provided sample data.

Run the main.py script:

```bash
python main.py
```

The script will train the Q-learning model and test it on the provided stock data. The output will display the total reward achieved by the model.

## Customization
You can customize the following hyperparameters in the main.py file:

- num_episodes (default: 1000): Number of training episodes for the Q-learning algorithm
- alpha (default: 0.1): Learning rate for the Q-learning algorithm
- gamma (default: 0.99): Discount factor for the Q-learning algorithm
- epsilon_start (default: 1.0): Initial exploration rate
- epsilon_end (default: 0.01): Minimum exploration rate
- epsilon_decay (default: 0.995): Exploration rate decay factor

You can also modify the StockTradingEnvironment class to change the stock trading environment's behavior, such as the maximum holding period.

License
This project is released under the MIT License. See the LICENSE file for details.
