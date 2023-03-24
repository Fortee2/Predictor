import gym
import numpy as np
import pandas as pd

class TradingEnv(gym.Env):
    def __init__(self, csv_file, window_size=50):
        self.window_size = window_size
        self.data = pd.read_csv(csv_file)
        self.reset()
        self.action_space = gym.spaces.Discrete(3)
        self.observation_space = gym.spaces.Box(low=0, high=1, shape=(window_size, 5), dtype=np.float32)

    def reset(self):
        self.current_step = 0
        self.position = 0
        self.history = []
        self.net_worth = 100
        self.shares_held = 0
        self.total_sales = 0
        self.data['norm_open'] = (self.data['open'] - self.data['open'].min()) / (self.data['open'].max() - self.data['open'].min())
        self.data['norm_close'] = (self.data['close'] - self.data['close'].min()) / (self.data['close'].max() - self.data['close'].min())
        self.data['norm_high'] = (self.data['high'] - self.data['high'].min()) / (self.data['high'].max() - self.data['high'].min())
        self.data['norm_low'] = (self.data['low'] - self.data['low'].min()) / (self.data['low'].max() - self.data['low'].min())
        self.data['norm_volume'] = (self.data['volume'] - self.data['volume'].min()) / (self.data['volume'].max() - self.data['volume'].min())
        return self._next_observation()

    def _get_reward(self, action):
        #TODO: May need to adjust reward function to reward buying and holding a position   
        current_price = self.data['close'][self.current_step]
        reward = 0
        if action == 0:  # Buy
            self.position = 1
        elif action == 1:  # Sell
            self.position = 0
            profit = (current_price * self.shares_held) - self.total_sales
            self.net_worth += profit
            reward = profit
            self.shares_held = 0
            self.total_sales = 0
        #else:  # Hold
            #self.position = self.position
        return reward

    def _next_observation(self):
        end = self.current_step + self.window_size
        obs = np.array([
            self.data['norm_open'].values[self.current_step:end],
            self.data['norm_close'].values[self.current_step:end],
            self.data['norm_high'].values[self.current_step:end],
            self.data['norm_low'].values[self.current_step:end],
            self.data['norm_volume'].values[self.current_step:end],
        ]).T
        return obs

    def step(self, action):
        current_price = self.data['close'][self.current_step]
        reward = self._get_reward(action)

        if action == 0 and self.net_worth > current_price:
            self.shares_held += 1
            self.net_worth -= current_price
            self.total_sales += current_price
        elif action == 1 and self.shares_held > 0:
            self.shares_held -= 1
            self.net_worth += current_price
            self.total_sales += current_price
        else:
            pass

        self.current_step += 1

        if self.current_step >= len(self.data) - 1:
            done = True
        else:
            done = False

