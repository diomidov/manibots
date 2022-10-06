from manifoldpy import api as mf
import numpy as np
import random
from time import time, sleep

API_KEY = '[REDACTED]'
MARKET_SLUG = 'will-biden-be-president-on-915-reso'
USER_ID = 'ymezf2YMJ9aaILxT95uWJj7gnx83'
OTHER_BOTS = ['w1knZ6yBvEhRThYPEYTwlmGv7N33', 'ilJdhpLzZZSUgzueJOs2cbRnJn82']

END_TIME = 1664247600 # 11 pm EDT
RESERVED_BASE_MANA = -100
RESERVED_HOURLY_MANA = 125
MAX_MARGINAL_BUDGET = 100
MIN_DELAY = 1 * 60
MAX_DELAY = 10 * 60
MIN_PROB = 0.5

def memoize(f):
    last_input = None
    last_output = None
    def helper(x):
        nonlocal last_input, last_output
        if x != last_input:
            last_input = x
            last_output = f(x)
        return last_output
    return helper

@memoize
def my_balance(market):
    return mf.get_user_by_id(USER_ID).balance


@memoize
def compute_marginal_budget(market):
    hours_left = (END_TIME - time()) / 60 / 60
    reserved = hours_left * RESERVED_HOURLY_MANA - RESERVED_BASE_MANA
    available_balance = my_balance(market) - reserved
    return min(MAX_MARGINAL_BUDGET, available_balance)

def compute_budget(market, target_prob):
    return min(compute_marginal_budget(market) * (market.probability - target_prob) * 100, my_balance(market) / 2)

@memoize
def get_limit_orders(market):
    return [(b.limitProb, b.orderAmount - b.amount) for b in market.bets if b.outcome == "YES" and b.limitProb and not b.isCancelled and not b.isFilled]

@memoize
def time_since_last_bet(market):
    return time() - max(b.createdTime / 1000 for b in market.bets)

def is_last_bet_mine(market):
    _, id = max((b.createdTime, b.userId) for b in market.bets)
    return id == USER_ID

def should_bet(market, target_prob):
    if target_prob >= market.probability - 0.01:
        return False

    budget = compute_budget(market, target_prob)
    # print(budget)
    limit_orders = get_limit_orders(market)
    budget -= sum(a * p / (1 - p) for p, a in limit_orders if p >= target_prob - 0.005)
    # print(budget)
    if budget <= 0:
        return False

    p = market.p
    y = market.pool['YES']
    n = market.pool['NO']
    new_y = y + budget
    new_n = np.exp(np.log(n) + p / (1 - p) * (np.log(y) - np.log(new_y)))
    new_prob = (p * new_n) / (p * new_n + (1 - p) * new_y)
    # print(new_prob * 100)

    return new_prob <= target_prob

def make_bets(market):
    for target_prob in np.arange(MIN_PROB, 1.0, 0.01):
        if should_bet(market, target_prob):
            budget = compute_budget(market, target_prob)
            print(f'Buy ${budget} NO to {target_prob * 100}% and cancel')
            id = mf.make_bet(API_KEY, budget, market.id, 'NO', target_prob).json()['betId']
            mf.cancel_bet(API_KEY, id)
            return
    print('Do not buy')

def main():
    while True:
        try:
            make_bets(mf.get_slug(MARKET_SLUG))
            print(f'Waiting for a new trade')
            while mf.get_slug(MARKET_SLUG).bets[0].userId == USER_ID:
                sleep(5)
            if mf.get_slug(MARKET_SLUG).bets[0].userId not in OTHER_BOTS:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                print(f'Waiting for {delay / 60} minutes')
                sleep(delay)
            else:
                sleep(5)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    main()