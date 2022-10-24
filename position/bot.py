from manifoldpy import api as mf
from time import sleep
from collections import defaultdict
from secret_config import API_KEY

USER_ID = "3S5gAHLCa3QgEAtC2D329hPPLY12"

def average_resolution(markets, include_prob=True):
    total = 0
    count = 0
    for m in markets:
        if m.isResolved and m.outcomeType == 'BINARY' and m.resolution != 'CANCEL':
            if m.resolution == 'YES':
                total += 1
                count += 1
            if m.resolution == 'NO':
                total += 0
                count += 1
            if m.resolution == 'MKT' and include_prob:
                total += m.resolutionProbability or m.probability
                count += 1
    return total / count

def print_stats():
    markets = mf.get_all_markets()
    print('Average prob including PROB:', average_resolution(markets, True))
    print('Average prob excluding PROB:', average_resolution(markets, False))




processed_market_ids = set()
creator_count = defaultdict(int)

def bet(m):
    print(f'Betting on {m.question}')
    mf.make_bet(API_KEY, 10, m.id, 'NO', limitProb=0.43)
    # mf.make_bet(API_KEY, 1, m.id, 'YES', limitProb=0.05)

def main():
    while True:
        for m in mf.get_markets(5):
            if m.id in processed_market_ids:
                continue
            processed_market_ids.add(m.id)

            creator_count[m.creatorId] += 1
            if creator_count[m.creatorId] >= 10:
                print(f'Too many markets from {m.creatorUsername}.')
                continue

            m = mf.get_market(m.id)
            if len(m.bets) == 0:
                bet(m)
        sleep(250)

if __name__ == '__main__':
    main()