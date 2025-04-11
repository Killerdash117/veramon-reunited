# Placeholder for models.
# For production, consider integrating an ORM like SQLAlchemy.

class User:
    def __init__(self, user_id, tokens=0, xp=0):
        self.user_id = user_id
        self.tokens = tokens
        self.xp = xp
        self.captures = []

class VeramonCapture:
    def __init__(self, veramon_name, caught_at, shiny, biome):
        self.veramon_name = veramon_name
        self.caught_at = caught_at
        self.shiny = shiny
        self.biome = biome

class InventoryItem:
    def __init__(self, item_id, quantity):
        self.item_id = item_id
        self.quantity = quantity
