import numpy as np
import pandas as pd
import random
from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
from DQNAgent import TradingEnv 
from DQNAgent import DQNAgent

import gym

# Define the trading environmentJust 
# Window size is the number of trading days to consider when making a decision
env = TradingEnv('ford_activity.csv', window_size=50)

# Define the agent
state_size = env.observation_space.shape[1]
action_size = env.action_space.n
agent = DQNAgent(state_size, action_size)

# Train the agent
#Batch is a subset of the training data that is used to update the model parameters during the training process
batch_size = 32
# Number of episodes to train the agent.  This is the number of times the agent will train on the entire dataset.
EPISODES = 50

for episode in range(1, EPISODES + 1):
    state = env.reset()
    state = np.reshape(state, [1, state_size])
    done = False
    total_profit = 0
    while not done:
        action = agent.act(state)
        next_state, reward, done, _ = env.step(action)
        total_profit += reward
        next_state = np.reshape(next_state, [1, state_size])
        agent.remember(state, action, reward, next_state, done)
        state = next_state
        if len(agent.memory) > batch_size:
            agent.replay(batch_size)
    print("episode: {}/{}, profit: {}".format(episode, EPISODES, total_profit))

# Save the trained model
agent.save('trained_model.h5')
