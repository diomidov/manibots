from manifoldpy import api as mf
import numpy as np
import scipy as sp
from time import sleep, time
from collections import namedtuple
import random

def shuffled(x):
    x = list(x)
    random.shuffle(x)
    return x

def cartesian_to_hyperbolic(p, y, n):
    r = y ** p * n ** (1 - p)
    phi = np.log(y / r) / (1 - p)
    return r, phi

def hyperbolic_to_cartesian(p, r, phi):
    return np.exp((1 - p) * phi) * r, np.exp(-p * phi) * r

def prob_from_cartesian(p, y, n):
    return (p * n) / (p * n + (1 - p) * y)

def my_balance():
    return mf.get_user_by_id(USER_ID).balance

class Backoff:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.t = 1
    
    def should_fire(self):
        if random.randrange(self.t) > 0:
            return False
        else:
            self.t = min(self.t * 2, MAX_BACKOFF)
            return True

class PlannedBet:
    def __init__(self, market, outcome, shares, cost):
        self.market = market
        self.outcome = outcome
        self.shares = shares
        self.cost = cost
    
    def __str__(self):
        if self.shares > 0:
            return f"{self.market.question}\n  Buy {self.shares} {self.outcome} shares for {self.cost}"
        else:
            return f"{self.market.question}\n  Sell {-self.shares} {self.outcome} shares for {-self.cost}"
            
    def execute(self):
        if self.shares > 0:
            mf.make_bet(API_KEY, self.cost, self.market.id, self.outcome)
        else:
            raise NotImplementedError('Selling is not supported yet')


class Group:
    def __init__(self, name, d):
        self.name = name
        self.slugs, m = zip(*d.items())
        m = np.array(m).T
        self.y_matrix = (m == 1).astype(float)
        self.n_matrix = (m == 0).astype(float)
        self.backoff = Backoff()


    def compute_profit_outcomes(self, dy, dn):
        return self.y_matrix @ dy + self.n_matrix @ dn

    def optimize(self, p, y, n):
        r, phi = cartesian_to_hyperbolic(p, y, n)

        def f(dphi):
            y2, n2 = hyperbolic_to_cartesian(p, r, phi + dphi)
            profit = self.compute_profit_outcomes(y - y2, n - n2)
            return -np.min(profit)
        
        # res = sp.optimize.minimize(f, method='CG', jac=True, x0=[-0.01, 0, 0.0263, 0, 0, 0])
        res = sp.optimize.differential_evolution(f, [(-1, 1)] * len(p))

        if res.success:
            y2, n2 = hyperbolic_to_cartesian(p, r, phi + res.x)
            profit = self.compute_profit_outcomes(y - y2, n - n2)
            return profit, y2, n2
        else:
            raise Exception('' + res.message + '\n' + str(res))

    def arbitrage(self):
        if not self.backoff.should_fire(): 
            return
        
        print()
        print(f'=== {self.name} ===')

        while True:
            markets = [mf.get_slug(slug) for slug in self.slugs]
            for m in markets:
                skip = skip_market(m)
                if skip:
                    print(skip)
                    print('Skipping group.')
                    self.backoff.reset()
                    return
            
            p = np.array([m.p for m in markets])
            y, n = get_shares(markets)
            print('Prior probs:    ', prob_from_cartesian(p, y, n))

            profit, y2, n2 = self.optimize(p, y, n)
            shares = n2 - n - y2 + y
            print('Posterior probs:', prob_from_cartesian(p, y2, n2))
            print('Profits:', profit)

            planned_bets = []
            for i, m in enumerate(markets):
                # TODO: sell instead of buying when possible
                if shares[i] > 0.5:
                    planned_bets.append(PlannedBet(m, 'YES', shares[i], n2[i] - n[i]))
                elif shares[i] < -0.5:
                    planned_bets.append(PlannedBet(m, 'NO', -shares[i], y2[i] - y[i]))
            
            if np.min(profit) <= 0.2 * len(planned_bets) + 0.01:
                print('Profit insufficient.')
                return

            self.backoff.reset()

            for bet in planned_bets:
                print(bet)

            if sum(b.cost for b in planned_bets if b.cost > 0) > my_balance():
                print("Insufficient balance!")
                return
            
            if CONFIRM_BETS and input('Proceed? (y/n)') != 'y':
                return

            # Make sure markets haven't moved
            if any(m.bets[0].createdTime != mf.get_bets(market=m.slug, limit=1)[0].createdTime for m in markets):
                print('Markets have moved!\nSkipping group.')
                return
            
            if API_KEY:
                for bet in planned_bets:
                    bet.execute()
            else:
                print('This is a dry run. Provide an API key to actually submit bets.')
                return

def skip_market(m):
    recent_bets = [b for b in m.bets if b.createdTime / 1000 >= time() - 60 * 60 and b.userId not in BOT_IDS]
    if m.isResolved:
        return f'Market "{m.question}" has resolved.'
    if m.closeTime / 1000 <= time() + 60 * 60:
        return f'Market "{m.question}" closes in less then an hour.'
    if any(b.createdTime / 1000 >= time() - 60 for b in recent_bets):
        return f'Market "{m.question}" has a trade in the last minute.'
    if m.probability <= 0.02:
        return f'Market "{m.question}" has probability <= 2%.'
    if m.probability >= 0.98:
        return f'Market "{m.question}" has probability >= 2%.'
    if any(b.probBefore <= 0.02 for b in recent_bets):
        return f'Market "{m.question}" recently had probability <= 2%.'
    if any(b.probBefore >= 0.98 for b in recent_bets):
        return f'Market "{m.question}" recently had probability <= 98%.'
    return None

def get_shares(markets):
    return np.array([m.pool['YES'] for m in markets]), np.array([m.pool['NO'] for m in markets])

def run_once(groups):
    print(f'Balance: {my_balance()}')
    for group in groups:
        try:
            group.arbitrage()
        except Exception as e:
            print(e)
    print()

def run(groups):
    while True:
        run_once(groups)
        sleep(SLEEP_TIME)

if __name__ == "__main__":
    from secret_config import *
    # from public_config import *
    groups = [Group(k, v) for k, v in GROUPS.items()]
    if RUN_ONCE:
        run_once(groups)
    else:
        run(groups)