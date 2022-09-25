from manifoldpy import api as mf
import numpy as np
import scipy as sp
from time import sleep, time
from collections import namedtuple
from random import shuffle

def shuffled(x):
    x = list(x)
    shuffle(x)
    return x

def cartesian_to_hyperbolic(p, y, n):
    r = y ** p * n ** (1 - p)
    phi = np.log(y / r) / (1 - p)
    return r, phi

def hyperbolic_to_cartesian(p, r, phi):
    return np.exp((1 - p) * phi) * r, np.exp(-p * phi) * r

def prob_from_cartesian(p, y, n):
    return (p * n) / (p * n + (1 - p) * y)

class Group:
    def __init__(self, name, d):
        self.name = name
        self.slugs, m = zip(*d.items())
        self.matrix = np.array(m).T


    def compute_profit_outcomes(self, dy, dn):
        return self.matrix @ dy + (1 - self.matrix) @ dn

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
        print()
        print(f'=== {self.name} ===')

        while True:
            markets = [mf.get_slug(slug) for slug in self.slugs]
            for m in markets:
                skip = skip_market(m)
                if skip:
                    print(skip)
                    print('Skipping group.')
                    return
            
            p = np.array([m.p for m in markets])
            y, n = get_shares(markets)
            print('Prior probs:    ', prob_from_cartesian(p, y, n))

            profit, y2, n2 = self.optimize(p, y, n)
            shares = n2 - n - y2 + y
            print('Posterior probs:', prob_from_cartesian(p, y2, n2))
            print('Profits:', profit)
            if np.min(profit) <= 0.1:
                print('Profit negligible, skipping')
                return

            for i, m in enumerate(markets):
                print(m.question)
                if shares[i] > 0.5:
                    print(f'  Buy {shares[i]} YES for M${n2[i] - n[i]}')
                elif shares[i] < -0.5:
                    print(f'  Buy {-shares[i]} NO for M${y2[i] - y[i]}')
                else:
                    print(f'  Do not trade')

            # TODO: make sure we can afford it!
            
            if CONFIRM_BETS and input('Proceed? (y/n)') != 'y':
                return

            # Make sure markets haven't moved
            if not np.allclose((y, n), get_shares([mf.get_slug(slug) for slug in self.slugs])):
                print('Markets have moved!\nSkipping group.')
            
            if API_KEY:
                for i, m in shuffled(enumerate(markets)):
                    if shares[i] > 0.5:
                        mf.make_bet(API_KEY, n2[i] - n[i], m.id, 'YES')
                    elif shares[i] < -0.5:
                        mf.make_bet(API_KEY, y2[i] - y[i], m.id, 'NO')
            else:
                print('This is a dry run. Provide an API key to actually submit bets.')
                return

def skip_market(m):
    if m.isResolved:
        return f'Market "{m.question}" has resolved'
    if m.closeTime / 1000 <= time() + 60 * 60:
        return f'Market "{m.question}" closes in less then an hour'
    if any(b.createdTime / 1000 >= time() - 60 for b in m.bets if b.userId != USER_ID):
        return f'Market "{m.question}" has a trade in the last minute'
    return None

def get_shares(markets):
    return np.array([m.pool['YES'] for m in markets]), np.array([m.pool['NO'] for m in markets])

def run_once(groups):
    for group in groups:
        try:
            group.arbitrage()
        except Exception as e:
            print(e)

def run(groups):
    while True:
        run_once(groups)
        sleep(60)

# from private import API_KEY, USER_ID, ALL_GROUPS

if __name__ == "__main__":
    # from secret_config import *
    from public_config import *
    groups = [Group(k, v) for k, v in GROUPS.items()]
    if RUN_ONCE:
        run_once(groups)
    else:
        run(groups)