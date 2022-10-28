from manifoldpy import api as mf
from time import sleep
from collections import defaultdict
from traceback import print_exception
import re

# from public_config import *
from secret_config import *

def average_resolution(markets, include_prob=True, include_unresolved=False):
    total = 0
    count = 0
    for m in markets:
        if m.isResolved:
            if m.resolution == 'YES':
                total += 1
                count += 1
            if m.resolution == 'NO':
                total += 0
                count += 1
            if m.resolution == 'MKT' and include_prob:
                total += m.resolutionProbability or m.probability
                count += 1
        elif include_unresolved:
            total += m.probability
            count += 1
    return total / count

def print_stats():
    markets = mf.get_all_markets()
    markets = [m for m in markets if m.outcomeType == 'BINARY']
    markets = [m for m in markets if m.creatorId not in CREATOR_BLACKLIST]
    markets = [m for m in markets if not any(re.search(w, m.question, re.I) for w in KEYWORD_BLACKLIST)]
    print('Average resolution including MKT:', average_resolution(markets, True))
    print('Average resolution excluding MKT:', average_resolution(markets, False))
    print('Average probability: ', average_resolution(markets, True, True))




processed_market_ids = set()
creator_count = defaultdict(int)

def bet(m):
    print(f'Betting')
    mf.make_bet(API_KEY, BET_AMOUNT, m.id, 'NO', limitProb=BET_LIMIT)
    # mf.make_bet(API_KEY, 1, m.id, 'YES', limitProb=0.05)

def process_market(m):
    if m.id in processed_market_ids:
        return
    processed_market_ids.add(m.id)

    m = mf.get_market(m.id)
    if len(m.bets) > 0 or m.isResolved or m.outcomeType != 'BINARY' or m.probability != 0.5:
        return

    print(f'New market by @{m.creatorUsername}: {m.question}')

    creator_count[m.creatorId] += 1
    if creator_count[m.creatorId] >= MAX_MARKETS_PER_CREATOR:
        print(f'Too many markets from {m.creatorUsername}.')
        return
    
    if m.creatorId in CREATOR_BLACKLIST:
        print(f'By blacklisted user {m.creatorUsername}')
        return

    for keyword in KEYWORD_BLACKLIST:
        if re.search(keyword, m.question, re.I):
            print(f'Contains blacklisted phrase {keyword}')
            return

    bet(m)

def main():
    print_stats()
    while True:
        try:
            for m in mf.get_markets(5):
                process_market(m)
        except Exception as e:
            print_exception(e)
        sleep(0.25)

if __name__ == '__main__':
    main()