# NEKOVA Package — random
# Random value generation

import importlib
import sys

# Force load Python's built-in random, not this file
_random = importlib.import_module("random")

def load() -> dict:
    return {
        "random_int":    lambda a, b: _random.randint(int(a), int(b)),
        "random_float":  lambda a, b: _random.uniform(float(a), float(b)),
        "random_choice": lambda lst: _random.choice(lst),
        "shuffle":       lambda lst: _random.sample(lst, len(lst)),
        "random_token":  lambda n=8: "".join(
            _random.choices("abcdefghijklmnopqrstuvwxyz0123456789",
                           k=int(n))),
    }
