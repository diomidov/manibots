from manifoldpy import api as mf
from time import time, sleep

API_KEY = '[REDACTED]'
MARKET_SLUG = 'what-of-petrov-day-will-elapse-befo'
USER_ID = 'ymezf2YMJ9aaILxT95uWJj7gnx83'
OTHER_BOTS = ['w1knZ6yBvEhRThYPEYTwlmGv7N33', 'ilJdhpLzZZSUgzueJOs2cbRnJn82']

START_TIME = 1664161200 # 11 pm EDT
END_TIME = 1664247600 # 11 pm EDT

def elapsed_percent(t):
    return (t - START_TIME) / (END_TIME - START_TIME)

def tick():
    elapsed = elapsed_percent(time())
    print(elapsed * 100)
    elapsed = round(elapsed, 2)
    m = mf.get_slug(MARKET_SLUG)
    if m.probability >= elapsed:
        return
    last_bet = [b for b in m.bets if b.userId not in OTHER_BOTS][0]
    print(last_bet.probAfter, elapsed_percent(last_bet.createdTime / 1000))
    if last_bet.outcome == 'NO' and last_bet.probAfter <= elapsed_percent(last_bet.createdTime / 1000) + 0.005:
        raise Exception('BOOM!')
    print(f'Bet up to {elapsed * 100}%')
    id = mf.make_bet(API_KEY, 20, m.id, 'YES', elapsed).json()['betId']
    mf.cancel_bet(API_KEY, id)

def main():
    while True:
        tick()
        sleep(10)

if __name__ == '__main__':
    main()