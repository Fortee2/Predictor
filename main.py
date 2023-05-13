import numpy as np
import pandas as pd
import random
import pickle
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
import gym
from gym import spaces    
import random
class StockTradingEnvironment(gym.Env):
    def __init__(self, data, max_holding_period=120):
        super(StockTradingEnvironment, self).__init__()
        self.data = data
        self.max_holding_period = max_holding_period
        self.current_step = 0
        self.current_holding_period = 0
        self.in_position = False
        self.capital = 10000

        self.action_space = spaces.Discrete(3)  # Buy, Sell, Hold
        #When adding new data points, make sure to update the shape of the observation space
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(11,), dtype=np.float32)

    def reset(self):
        self.current_step = 0
        self.current_holding_period = 0
        self.capital = 10000 
        self.in_position = False
        return self.get_state()

    def get_state(self):
        #when adding new data points, make sure to update the state
        return self.data.iloc[self.current_step][[ 'open','close', 'volume', 'high', 'low','MACD','Signal', 'rsi', 'market_updown']].values

    def take_action(self, action):
        if action == 0:  # Buy
            if not self.in_position:
                self.in_position = True
                self.current_holding_period = 0
                self.capital -= self.data.iloc[self.current_step]['close']
        elif action == 1:  # Sell
            if self.in_position:
                self.in_position = False
                self.current_holding_period = 0
                self.capital += self.data.iloc[self.current_step]['close']
        else:  # Hold
            pass

    def step(self, action):
        self.current_step += 1
        self.current_holding_period += 1
        
        if self.current_step >= len(self.data) - 1:  # Add capital check here
            done = True
        else:
            done = False

        if self.in_position and not done:
            reward = self.data.iloc[self.current_step + 1]['close'] - self.data.iloc[self.current_step]['close']
        else:
            reward = 0
        
        self.take_action(action)
        
        if self.in_position and self.current_holding_period >= self.max_holding_period:  
            self.in_position = False
            self.current_holding_period = 0
            self.capital += self.data.iloc[self.current_step]['close']
            
        next_state = self.get_state()
        return next_state, reward, done, {}

def preprocess_data(data):
    data = data.copy()
       
    print(data.columns)
    
    data.dropna(inplace=True) 
    scaler = StandardScaler()
    data[['open','close', 'volume', 'high', 'low','MACD','Signal', 'rsi', 'market_updown']] = scaler.fit_transform(data[['open','close', 'volume', 'high', 'low','MACD','Signal', 'rsi', 'market_updown']])
    
    return data, scaler

def q_learning(env, num_episodes=6000, alpha=0.1, gamma=0.99, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.999 ):
    q_table = defaultdict(lambda: np.zeros(env.action_space.n))

    for episode in range(num_episodes):
        state = env.reset()
        state = tuple(state)

        epsilon = epsilon_start * (epsilon_decay ** episode)

        done = False
        while not done:
            if random.uniform(0, 1) < epsilon:
                action = env.action_space.sample()
            else:
                action = np.argmax(q_table[state])

            next_state, reward, done, _ = env.step(action)
            next_state = tuple(next_state)

            best_next_action = np.argmax(q_table[next_state])
            td_target = reward + gamma * q_table[next_state][best_next_action]
            q_table[state][action] += alpha * (td_target - q_table[state][action])

            state = next_state

        epsilon = max(epsilon * epsilon_decay, epsilon_end)

    return q_table

# Define the new function here
def test_q_learning(q_table, env):
    state = env.reset()
    state = tuple(state)
    done = False
    total_reward = 0

    while not done:
        action = np.argmax(q_table[state])
        next_state, reward, done, _ = env.step(action)
        next_state = tuple(next_state)
        state = next_state
        total_reward += reward
    
    # Add the logic for returning a buy, sell, or hold recommendation
    if action == 0:
        return "Buy"
    elif action == 1:
        return "Sell"
    else:
        return "Hold"
    
def inverse_transform_close_price(scaler, value):
    dummy_data = np.zeros((1, scaler.scale_.shape[0]))
    dummy_data[0, 1] = value  # 'close' is the second column in the standardized data
    return scaler.inverse_transform(dummy_data)[0, 1]

def test_harness(historical_data, q_table, scaler, starting_capital=1000):
    env = StockTradingEnvironment(historical_data)
    state = env.reset()
    state = tuple(state)

    capital = starting_capital
    num_shares = 0
    actions_log = []

    for _ in range(len(historical_data) - 1):
        action = np.argmax(q_table[state])
        actions_log.append((env.current_step, action))

        if action == 0:  # Buy
            if not env.in_position:
                close_price = inverse_transform_close_price(scaler, env.data.iloc[env.current_step]['close'])
                num_shares_to_buy = capital // close_price
                if num_shares_to_buy > 0:
                    num_shares += num_shares_to_buy
                    capital -= num_shares_to_buy * close_price
                    env.in_position = True
                    env.current_holding_period = 0
        elif action == 1:  # Sell
            if env.in_position:
                close_price = inverse_transform_close_price(scaler, env.data.iloc[env.current_step]['close'])
                capital += num_shares * close_price
                num_shares = 0
                env.in_position = False
                env.current_holding_period = 0

        env.capital = capital
        state, _, done, _ = env.step(action)
        state = tuple(state)

        if done or capital <= 0:
            break

    # Sell any remaining shares at the end of the simulation
    if env.in_position:
        close_price = inverse_transform_close_price(scaler, env.data.iloc[env.current_step]['close'])
        capital += num_shares * close_price
        num_shares = 0

    profit_or_loss = capital - starting_capital
    return profit_or_loss, actions_log

def save_q_table(q_table, file_name):
    q_table_dict = dict(q_table)
    with open(file_name, 'wb') as f:
        pickle.dump(q_table_dict, f)

def load_q_table(file_name):
    with open(file_name, 'rb') as f:
        q_table_dict = pickle.load(f)
    q_table = defaultdict(lambda: np.zeros(len(q_table_dict[list(q_table_dict.keys())[0]])), q_table_dict)
    return q_table

def main():
    # Load dataset
    data = pd.read_csv('celanse_activity.csv')  # Replace with your S&P 500 stock data file

    # Preprocess data
    data, scaler = preprocess_data(data)

    # Split data into training and testing
    train_data = data.iloc[:-252]  # Use all data except the last year for training
    test_data = data.iloc[-252:]  # Use the last year for testing
 
    # Create the environment
    train_env = StockTradingEnvironment(train_data)
    test_env = StockTradingEnvironment(test_data)

    # Define the range for epsilon decay
    epsilon_decay_range = [0.7, 0.999]

    # Define the number of random search iterations
    num_iterations = 100

    # Keep track of the best decay rate and corresponding profit/loss
    best_decay_rate = None
    best_profit_or_loss = -float('inf')

    for i in range(num_iterations):
        # Randomly sample a decay rate from the range
        decay_rate = random.uniform(epsilon_decay_range[0], epsilon_decay_range[1])

        # Train the Q-learning model with the current decay rate
        q_table = q_learning(train_env, num_episodes=6000, epsilon_decay=decay_rate)

        # Evaluate the model using the test harness
        profit_or_loss, _ = test_harness(test_data, q_table, scaler, starting_capital=10000)

        print(f"Iteration {i+1}/{num_iterations}: Decay Rate = {decay_rate}, Profit/Loss = ${profit_or_loss:.2f}")

        # Update the best decay rate and profit/loss if this is the best one so far
        if profit_or_loss > best_profit_or_loss:
            best_decay_rate = decay_rate
            best_profit_or_loss = profit_or_loss

    print(f"Best Decay Rate = {best_decay_rate}, Best Profit/Loss = ${best_profit_or_loss:.2f}")

    # Test the Q-learning model
    # recommendation = test_q_learning(q_table, test_env)   
    # print(f'Recommended action: {recommendation}')
    

if __name__ == "__main__":
    main()
