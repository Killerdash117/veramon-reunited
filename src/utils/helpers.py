def weighted_choice(choices):
    """
    Given a list of tuples (choice, weight), return one item based on weighted randomness.
    """
    import random
    total = sum(weight for item, weight in choices)
    r = random.uniform(0, total)
    upto = 0
    for item, weight in choices:
        if upto + weight >= r:
            return item
        upto += weight
    return choices[0][0]
