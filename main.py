import numpy as np
import pandas as pd
import random
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
import gym
from gym import spaces

class StockTradingEnvironment(gym.Env):
    def __init__(self, data, max_holding_period=20):
        super(StockTradingEnvironment, self).__init__()
        self.data = data
        self.max_holding_period = max_holding_period
        self.current_step = 0
        self.current_holding_period = 0
        self.in_position = False

        self.action_space = spaces.Discrete(3)  # Buy, Sell, Hold
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(4,), dtype=np.float32)

    def reset(self):
        self.current_step = 0
        self.current_holding_period = 0
        self.in_position = False
        return self.get_state()

    def get_state(self):
        return self.data.iloc[self.current_step][['close', '7-day', '14-day', '21-day']].values

    def step(self, action):
        self.current_step += 1
        self.current_holding_period += 1

        if self.current_step >= len(self.data) - 1:
            done = True
        else:
            done = False

        if self.in_position and not done:
            reward = self.data.iloc[self.current_step + 1]['close'] - self.data.iloc[self.current_step]['close']
        else:
            reward = 0

        if action == 0:  # Buy
            if not self.in_position:
                self.in_position = True
                self.current_holding_period = 0
        elif action == 1:  # Sell
            if self.in_position:
                self.in_position = False
                self.current_holding_period = 0
        else:  # Hold
            pass

        if self.in_position and self.current_holding_period >= self.max_holding_period:
            self.in_position = False
            self.current_holding_period = 0

        next_state = self.get_state()

        return next_state, reward, done, {}

def preprocess_data(data):
    data = data.copy()
    data['7-day'] = data['close'].rolling(window=7).mean()
    data['14-day'] = data['close'].rolling(window=14).mean()
    data['21-day'] = data['close'].rolling(window=21).mean()
    data.dropna(inplace=True)
    scaler = StandardScaler()
    data[['close', '7-day', '14-day', '21-day']] = scaler.fit_transform(data[['close', '7-day', '14-day', '21-day']])
    return data

def q_learning(env, num_episodes=1000, alpha=0.1, gamma=0.99, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995):
    q_table = defaultdict(lambda: np.zeros(env.action_space.n))
    epsilon = epsilon_start

    for episode in range(num_episodes):
        state = env.reset()
        state = tuple(state)

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
    
    return q_table  # Add this line

def main():
    # Load dataset
    data = pd.read_csv('ford_activity.csv')  # Replace with your S&P 500 stock data file

    # Preprocess data
    data = preprocess_data(data)

    # Split data into training and testing
    train_data = data.iloc[:-252]  # Use all data except the last year for training
    test_data = data.iloc[-252:]  # Use the last year for testing

    # Create the environment
    train_env = StockTradingEnvironment(train_data)
    test_env = StockTradingEnvironment(test_data)

    # Train the Q-learning model
    q_table = q_learning(train_env, num_episodes=1000)

    # Test the Q-learning model
    state = test_env.reset()
    state = tuple(state)
    done = False
    total_reward = 0

    while not done:
        action = np.argmax(q_table[state])
        next_state, reward, done, _ = test_env.step(action)
        next_state = tuple(next_state)
        state = next_state
        total_reward += reward

    print(f'Total reward: {total_reward}')

if __name__ == "__main__":
    main()
