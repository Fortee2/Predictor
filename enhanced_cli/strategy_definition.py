# This file will handle the definition and loading of the trading strategy

strategy_context = None

def load_strategy(strategy_text):
    # Logic to load the strategy text as context for the AI session
    global strategy_context
    try:
        strategy_context = strategy_text
        print(f"Strategy loaded: {strategy_text}")
    except Exception as e:
        pass


def save_session_to_diary(session_data):
    # Logic to save the session data to the trading diary
    try:
        with open("trading_diary.txt", "a") as diary:
            diary.write(session_data + "\n")
    except Exception as e:
        pass
