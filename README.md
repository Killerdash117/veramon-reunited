
# Veramon Reunited
*A fully-featured Discord RPG bot created by Killerdash117*

This bot brings monster-catching, battling, faction-building, and PvP together in a multiplayer-first RPG experience on Discord.

---

## 🌟 Core Features

- 300+ unique Veramons with evolutions and rarities
- 315+ abilities, elemental types, and type effectiveness
- PvE & PvP battles, raid bosses, and shiny hunting
- Factions (upgradeable organizations) and small guilds
- Player economy with shops, market, quests, and crafting
- Full cosmetic system (titles, auras, frames, banners)
- VIP system with no pay-to-win mechanics
- Developer/Admin/Moderator rank systems
- Custom profiles, leaderboards, achievements, and more

---

## 🎯 Catching System (Detailed)

Veramon Reunited includes a fully modular catching engine built on JSON data. It supports:

### Biomes
Located in `data/biomes.json`, each biome includes:
- A description
- Spawn table by rarity (common, uncommon, rare, etc.)
- Can be expanded with terrain tags, level ranges, and weather effects

### Veramon Data
Stored in `data/veramon_data.json`, each Veramon includes:
- Name, rarity, type(s)
- Evolution stage
- Catch rate (0.0 to 1.0)
- Base stats (for battle logic)
- Flavor text
- Biome availability
- (Optional) shiny images or lore

### Commands

| Command     | Description                                      |
|-------------|--------------------------------------------------|
| `/explore`  | Choose a biome and find a wild Veramon           |
| `/catch`    | Attempt to catch the encountered Veramon         |

### Mechanics
- Spawn chance is tied to rarity and biome
- Shiny chance is 1-in-2000 by default
- Catch chance is determined per-Veramon (from data file)
- Encounters are per-player (no multi-catch exploit)

---

## 📁 Project Structure

```
veramon_reunited/
├── bot.py
├── requirements.txt
├── README.md
├── cogs/
│   └── catching_cog.py
├── data/
│   ├── veramon_data.json
│   └── biomes.json
```

---

## ⚙️ How to Add New Veramons

1. Open `data/veramon_data.json`
2. Add a new Veramon with:
```json
"Mythogryph": {
  "name": "Mythogryph",
  "rarity": "legendary",
  "type": ["Astral", "Steel"],
  "evolution_stage": "final",
  "catch_rate": 0.2,
  "base_stats": {"hp": 85, "atk": 100, "def": 95},
  "biomes": ["mountains", "ruins"],
  "flavor": "Said to descend from the stars themselves."
}
```

3. Add it to a biome’s spawn table in `biomes.json`

---

## ✅ Credits

**Veramon Reunited** was created and designed by **Killerdash117**

