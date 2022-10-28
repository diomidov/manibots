API_KEY = "[redacted]"

BET_AMOUNT = 15              # Bet this much
BET_LIMIT = 0.40             # Don't bet below this probability

MAX_MARKETS_PER_CREATOR = 10 # Don't trade on more than this many markets from single creator
CREATOR_BLACKLIST = [        # Do not trade if market is from one of these users
    'Y8xXwCCYe3cBCW5XeU8MxykuPAY2', # Yev
]
KEYWORD_BLACKLIST = [        # Do not trade if title contains any of these regexes
    r'^test\b',
]