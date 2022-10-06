from manifoldpy import api as mf
from time import sleep

API_KEY = "[REDACTED]"
USERNAME = "LiquidityBonusBot"

def should_exploit(market):
    # Only bet on binary CPMM markets
    if market.outcomeType != 'BINARY' or market.mechanism != 'cpmm-1':
        return False
    # Don't try to bet on resolved markets
    if market.isResolved:
        return False
    # Skip own markets
    if market.creatorUsername == USERNAME:
        return False
    # Skip markets on which you've already bet
    if len(mf.get_bets(market=market.slug, username=USERNAME)) > 0:
        return False
    # Skip markets with any limit orders
    if any(b.limitProb != None for b in mf.get_bets(market=market.slug)):
        return False
    return True

def exploit(market):
    outcome = "YES" if market.probability <= 0.5 else "NO"
    amount = 1000
    mf.make_bet(API_KEY, amount, market.id, outcome)
    for i in range(20):
        if mf.get_market(market.id).totalLiquidity != market.totalLiquidity:
            break
        sleep(0.2)
    mf.sell_shares(API_KEY, market.id, outcome)

def exploit_recent():
    markets = mf.get_markets(20)
    for m in markets:
        if should_exploit(m):
            print("Market:", m.question)
            print("By:", m.creatorName)
            if input('Exploit? [y/n]') != 'y':
                continue
            exploit(m)

if __name__ == "__main__":
    exploit_recent()