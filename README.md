# Veramon Reunited – The Ultimate Discord Monster RPG Bot

**Created by Killerdash117**

---

## Overview

Veramon Reunited is an advanced, multiplayer-first Discord bot that delivers a rich monster-catching RPG experience right within your server. Inspired by classic creature-collecting games yet reimagined for persistent multiplayer action, this bot is built for communities that crave long-term progression, in-depth customization, and competitive as well as cooperative gameplay.

---

## Key Features

### 1. Comprehensive Creature System
- **300+ Unique Veramons:**  
  Each creature ("Veramon") is defined in JSON format with:
  - **Types & Evolutions:** Single or dual types with multiple evolution stages.
  - **Base Stats:** Detailed statistics for HP, Attack, Defense, etc.
  - **Rarity Levels:** Ranging from *common* and *uncommon* to *rare*, *legendary*, and *mythic*.
  - **Shiny Variants:** An ultra-rare alternate form with distinct aesthetics.
  - **Flavor Text:** Engaging lore for each creature.
  
- **Modular Data Files:**  
  Easily extend the creature roster by updating `src/data/veramon_data.json`.

---

### 2. Dynamic Spawning & Catching Mechanics
- **Biome-Based Encounters:**  
  - Explore various biomes (e.g., forest, cave, volcano, lake) as defined in `src/data/biomes.json`.
  - Each biome features its own weighted spawn table, ensuring diverse and context-appropriate encounters.

- **Advanced Encounter System:**  
  - Uses a weighted random selection algorithm to determine which Veramon appears.
  - Incorporates environment modifiers and rarity weighting.

- **Capture System:**  
  - Command-driven capture with `/explore` and `/catch` (slash commands).
  - Capture chance is calculated from the Veramon's base catch rate modified by catch items.
  - Supports different catch items (e.g., Standard Capsule, Ultra Capsule, Golden Lure) defined in `src/data/items.json`.

- **Persistent Logging:**  
  - Successful captures are recorded in a SQLite database (see `src/db/db.py`) with details like catch time, shiny status, and biome.

---

### 3. Battle System (Planned/Prototype)
- **Turn-Based Combat:**  
  - A foundational battle engine where player creatures can engage wild Veramons.
  - Incorporates basic stats (attack, defense, HP) with a simple damage formula.
  
- **Future Enhancements:**  
  - Expand to PvP duels, real-time battles, critical hits, and advanced abilities.
  - Integrate detailed animations and interactive battle choices.

---

### 4. Economy & Inventory
- **In-Game Currencies:**  
  - Tokens, Crystals, and other future currencies designed to balance reward and progression.
  
- **Item Shops & Crafting:**  
  - Use catch items and upgrade gear via an in-game shop/auction house.
  
- **Inventory Management:**  
  - Track your items and captured Veramons persistently.
  - Commands such as `/inventory` to show your current collection and resources.

---

### 5. Multiplayer and Social Systems
- **Factions & Guilds:**  
  - **Guilds:** Small parties (max 5 members) for casual cooperative play.
  - **Factions:** Larger, upgradeable organizations offering unique benefits, raid events, and shared resources. Faction upgrades include combat buffs, exclusive dungeons, and economy improvements.
  
- **Profile Customization:**  
  - Create and customize your profile with titles, auras, badges, and custom banners.
  - Display your achievements, XP, and captured Veramons with the `/profile` command (coming soon).

- **Role-Based Permissions:**  
  - Commands are segregated based on user roles: **Dev**, **Admin**, **Mod**, **VIP**, and **User**.
  - Provides robust control with dedicated admin and moderation tools.

---

### 6. Persistent Data and Extensible Architecture
- **SQLite Database:**  
  - Stores user captures and inventory in a persistent manner (see `src/db/db.py`).
  
- **Modular Codebase:**  
  - Organized into clear directories:
    - **`src/cogs/`**: Contains Discord command modules (catching, battles, etc.).
    - **`src/data/`**: Houses JSON files for Veramons, biomes, and items.
    - **`src/db/`**: Manages database connections and schema initialization.
    - **`src/models/`**: Placeholder for data models (expandable via ORM like SQLAlchemy).
    - **`src/utils/`**: Utility functions (e.g., weighted random selection).
    - **`src/config/`**: Global configuration settings for the bot.
  
- **Future-Proof Design:**  
  - Easily extend the system by adding new modules (battle engine, quests, profiles, PvP, etc.).
  - Designed for scalability, security, and ease of maintenance.
