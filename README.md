# Veramon Reunited
[![license](http://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/killerdash117/veramon-reunited/blob/master/LICENSE)
[![version](https://img.shields.io/badge/version-v0.15-brightgreen.svg)](https://github.com/killerdash117/veramon-reunited/releases)
[![discord.py](https://img.shields.io/badge/discord.py-2.3.0-blue.svg)](https://github.com/Rapptz/discord.py)
[![status](https://img.shields.io/badge/status-in%20development-orange.svg)](https://github.com/killerdash117/veramon-reunited)

<div align="center">

![Veramon Reunited](https://i.imgur.com/EMNMEsp.jpeg)

**A feature-rich monster-catching Discord bot**  
*Created by Killerdash117*

[Setup Guide](#setup) • [Features](#features) • [Commands](#commands) • [Developer Guide](#for-developers) • [Contributing](#contributing)

</div>

---

## Overview

Veramon Reunited delivers a rich monster-catching RPG experience within Discord. Inspired by classic creature-collecting games yet reimagined for persistent multiplayer action, this bot is built for communities that crave long-term progression, in-depth customization, and both competitive and cooperative gameplay.

### Quick Links
- [Invite Bot](#setup) - Add Veramon Reunited to your server
- [GitHub Repository](https://github.com/killerdash117/veramon-reunited) - View source code and contribute

---

## Features

### Creature System
- **300+ Unique Veramons** with detailed stats, types, evolutions, abilities, and rarities
- **Shiny Variants** with distinct aesthetics and boosted properties
- **Evolution Chains** allowing Veramon to transform as they grow stronger
- **Modular Data Files** making it easy to extend the creature roster

### Dynamic Exploration
- **Biome-Based Encounters** across various environments (forests, caves, volcanoes, etc.)
- **Advanced Spawn Algorithm** with weighted selection based on rarity and environment
- **Capture System** with different items affecting catch rates
- **Persistent Logging** of all captures with detailed metadata

### Battle System
- **Turn-Based Combat** with stats, type advantages, and abilities
- **Player vs Player (PvP)** battles to compete against other trainers
- **Player vs Environment (PvE)** battles against NPC trainers
- **Multi-Player Battles** with up to 4 players (2v2 or Free-for-All)
- **Interactive Battle UI** with move selection and battle feedback
- **Type Effectiveness** system with strengths and weaknesses
- **Battle Rewards** including XP, tokens, and evolution opportunities
- **Commands:**
  - `/battle_pve [difficulty]` - Battle against an NPC trainer
  - `/battle_pvp [player]` - Challenge another player to a battle
  - `/battle_multi [type] [team_size]` - Start a multi-player battle

### Economy & Inventory
- **Token System** for purchasing items and upgrades
- **Item Shop** with catch tools, boosts, and cosmetics
- **Inventory Management** for organizing your collection
- **Trading System** for exchanging with other players
  - Player-to-player Veramon trading
  - Trade verification to prevent scams
  - Trade history tracking
  - Commands:
    - `/trade_create` - Start a trade with another player
    - `/trade_add` - Add a Veramon to the trade
    - `/trade_remove` - Remove a Veramon from the trade
    - `/trade_cancel` - Cancel an active trade
    - `/trade_list` - View active and recent trades

### Social Systems

#### Guild System
- Small parties (max 5 members) for casual cooperative play
- **Commands:**
  - `/guild_create` - Start a new guild
  - `/guild_join` - Join an existing guild
  - `/guild_info` - View guild details
  - `/guild_leave` - Leave your current guild
  - `/guild_invite` - Invite a player to your guild
  - `/guild_kick` - Remove a member
  - `/guild_promote` - Promote a member to officer or leader

#### Faction System
- Large organizations (up to 50 members) with extensive features:
- **Hierarchical Structure** with customizable ranks and permissions
- **Upgrades System** providing permanent benefits to all members
- **Treasury** for shared economic resources
- **Territory Control** for resource bonuses
- **Faction Wars** for competition and dominance
- **Temporary Buffs** for strategic advantages
- **Commands:**
  - `/faction_create` - Create a new faction (Admin only)
  - `/faction_join` - Request to join a faction
  - `/faction_info` - View faction details
  - `/faction_leave` - Leave your current faction
  - `/faction_upgrade` - Purchase permanent faction upgrades
  - `/faction_buff` - Activate temporary faction-wide buffs
  - `/faction_war` - Declare war on another faction

### Admin Command System
- **Veramon Management:**
  - `/admin_add_veramon` - Add a new Veramon to the game
  - `/admin_edit_veramon` - Edit an existing Veramon's properties
  - `/admin_give_veramon` - Give a Veramon to a player (with customizable level, shiny status)
- **Ability Management:**
  - `/admin_add_ability` - Add a new ability with custom effects
- **Game Settings:**
  - `/admin_config_rarity` - Configure rarity tier settings (catch rates, spawn weights, rewards)
  - `/admin_evolution_rules` - Adjust evolution mechanics (level multipliers, stat boosts)
  - `/admin_battle_settings` - Fine-tune battle system parameters
  - `/admin_spawn_rate` - Adjust spawn rates for specific biomes
- **Data Management:**
  - `/admin_export_data` - Export game data to JSON for backup purposes
  - `/admin_import_data` - Import game data from backups
  - `/admin_rebuild_db` - Rebuild database tables (with option to preserve data)

### Role-Based Permissions
- **User:** Basic gameplay commands (exploring, catching, battling)
- **VIP:** Premium features (faster cooldowns, increased catch rates, exclusive items)
- **Mod:** Moderation tools and event management capabilities
- **Admin:** Full server control (faction creation, economy management)
- **Dev:** System-level commands and database access

### Progression Systems
- **Experience** gained through activities
- **Leveling** for both trainers and Veramon
- **Evolution** of Veramon when meeting requirements
- **Achievements** for completing challenges

---

## Setup

1. **Invite the bot** to your Discord server
2. **Configure roles** to match the permission levels:
   - User (or Veramon Trainer)
   - VIP (or Premium)
   - Mod (or Moderator)
   - Admin (or Administrator)
   - Dev (or Developer)
3. **Start playing** with the `/help` command

---

## For Developers

### Getting Started

To set up this bot for development:

```bash
# Clone the repository
git clone https://github.com/killerdash117/veramon-reunited.git
cd veramon-reunited

# Install dependencies
pip install -r requirements.txt

# Create .env file with your bot token
echo "DISCORD_TOKEN=your-token-here" > .env

# Run the bot
python main.py
```

### Code Examples

#### Adding New Veramon

```json
// src/data/veramon_data.json
{
  "Flametar": {
    "id": 25,
    "types": ["fire"],
    "base_stats": {
      "hp": 45, "attack": 65, "defense": 40,
      "sp_attack": 60, "sp_defense": 45, "speed": 70
    },
    "abilities": ["flame_body", "blaze"],
    "catch_rate": 45,
    "evolution": {
      "evolves_to": "Blazitar",
      "level_required": 16
    },
    "rarity": "uncommon",
    "flavor_text": "A newly discovered fire-type that lives in volcanic areas."
  }
}
```

#### Creating a New Command

```python
@app_commands.command(name="command_name", description="Command description")
@require_permission_level(PermissionLevel.USER)  # Set required permission level
async def command_name(self, interaction: discord.Interaction, param: str):
    """Detailed docstring for the command."""
    user_id = str(interaction.user.id)
    
    # Database interaction
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM table WHERE user_id = ?", (user_id,))
    
    # Create response embed
    embed = discord.Embed(
        title="Command Result",
        description=f"Command executed with parameter: {param}",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed)
```

#### Adding a New Biome

```json
// src/data/biomes.json
{
  "crystal_cavern": {
    "name": "Crystal Cavern",
    "description": "A stunning cavern with glowing crystals and rare minerals.",
    "veramon_spawns": {
      "common": ["Crystalite", "Geolite", "Mineralon"],
      "uncommon": ["Gemling", "Quartzite"],
      "rare": ["Diamondite", "Emeraldian"],
      "legendary": ["Prismatic"]
    },
    "spawn_weights": {
      "common": 70, "uncommon": 20, "rare": 9, "legendary": 1
    }
  }
}
```

#### Using the Permission System

```python
# Apply permission checking to commands
@require_permission_level(PermissionLevel.ADMIN)
async def admin_only_command(self, interaction): 
    # Only ADMIN and above can run this command
    
# Get user perks based on their permission level
user_perks = get_user_perks(interaction)
catch_rate_bonus = user_perks.get("catch_rate_bonus", 0)

# Check available commands for a permission level
available_commands = get_available_commands(PermissionLevel.VIP)
```

#### Extending the Faction System

```python
@app_commands.command(name="faction_quest", description="Start a faction quest")
@require_permission_level(PermissionLevel.USER)
async def faction_quest(self, interaction: discord.Interaction, quest_type: str):
    # Check if user is in a faction
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT f.faction_id, f.name, fr.permissions
        FROM faction_members fm
        JOIN factions f ON fm.faction_id = f.faction_id
        JOIN faction_ranks fr ON fm.rank_id = fr.rank_id
        WHERE fm.user_id = ?
    """, (str(interaction.user.id),))
```

### Database Schema

The SQLite database includes these key tables:

| Table | Purpose |
|-------|---------|
| `users` | Player profiles and data |
| `veramon_captures` | Record of all captures |
| `inventory` | Items owned by players |
| `guilds` & `guild_members` | Small group management |
| `factions` & related tables | Large organization system |
| `faction_wars` & `faction_territories` | Competitive gameplay |
| `faction_buffs` & `faction_upgrades` | Progression mechanics |

---

For a detailed history of all changes and version information, see the [CHANGELOG.md](CHANGELOG.md) file.

---

## Contributing

We welcome contributions to Veramon Reunited! Here's how to get started:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the existing code style and organization
- Add appropriate documentation for new features
- Include tests for new functionality when possible
- Ensure your code works with existing systems

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Credits

- Built with [Discord.py](https://github.com/Rapptz/discord.py) v2.3.0
- Created by [Killerdash117](https://github.com/killerdash117)
