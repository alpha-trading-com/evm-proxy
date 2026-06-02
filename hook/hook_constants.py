from app.constants import NETWORK

NETWORK = "ws://127.0.0.1:9944"
SEEN_MAX = 1500
EXTRINSIC_START_CALL = 'START_CALL'
EXTRINSIC_SUBMIT_ENCRYPTED = 'SUBMIT_ENCRYPTED'
ROOT_NETUID = 0


STAKE_AMOUNT_TAO = 200
MIN_STAKE_RAO = 1000_000_001
# netuid -> TAO per alpha; move all stake to root when price is above this
WHITELISTED_SUBNETS = [16, 40, 58, 92, 72]
BLACK_LISTED_COLDKEYS = [
    "5CqRkhQUEgkQ4nBB4SCKnc9AzKPs9VLYv28erjeXPqQYVt9V", 
    "5F9Qvcz22Fwq4cm58o2bShiL6n8BnJmhqXB1cispBpqRfN6w",
    "5CigXk8XsnSqi8unxvYma6n8wYD35obs1XCS9eibjFF4vYEN",
    "5DPhE2hhn6Bbn8QzrFMBTdtZR1QD9NEZDjRv256ppvpJNW92",
    "5HTYVBxrF2WbVN8RBtFxAkBGuHJxjgLd9Sze5gxH4KC6GLCv",
]

UNSTAKE_TO_ROOT_IF_PRICE_ABOVE: dict[int, float] = {
    16: 0.02,
    40: 0.02,
    58: 0.02,
    92: 0.02,
    72: 0.02,
}