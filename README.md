<div align="center">

# 🌟 Veramon Reunited 🌟

<img src="https://i.imgur.com/EMNMEsp.jpeg" alt="Veramon Reunited" width="500"/>

[![license](http://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/killerdash117/veramon-reunited/blob/master/LICENSE)
[![version](https://img.shields.io/badge/version-v0.33.000-brightgreen.svg)](https://github.com/killerdash117/veramon-reunited/releases)
[![discord.py](https://img.shields.io/badge/discord.py-2.3.0-blue.svg)](https://github.com/Rapptz/discord.py)
[![status](https://img.shields.io/badge/status-in%20development-orange.svg)](https://github.com/killerdash117/veramon-reunited)
[![author](https://img.shields.io/badge/author-killerdash117-purple.svg)](https://github.com/killerdash117)

**A comprehensive Discord bot for monster-catching adventures in your server**

[Features](#-features) • [Commands](#-commands) • [Setup Guide](#-setup-guide) • [Developer Guide](#-developer-guide) • [Contributing](#-contributing)

</div>

---

## 🔍 Overview

**Veramon Reunited** transforms your Discord server into an immersive monster-catching RPG experience. Capture unique creatures, battle other trainers, join factions, and explore a vast world—all through intuitive Discord commands and interactive UI elements.

Inspired by classic creature-collecting games but completely redesigned for Discord interactions, Veramon Reunited offers a persistent world where progress continues even when you're offline. With over 300 creatures to collect, a deep battle system using Discord buttons, faction wars, and regular events, there's always something new to discover without ever leaving your server.

### Why Choose Veramon Reunited?

- **Built for Discord** - Designed from the ground up for Discord's interface and social dynamics
- **Comprehensive Gameplay** - Deep systems for battling, trading, exploring, and collecting
- **Community Focus** - Parties, factions, trading, and PvP foster player interaction
- **Interactive UI** - Intuitive button-based controls rather than memorizing commands
- **Continuous Development** - Regular updates with new features and content
- **Balance First** - Designed for long-term engagement without pay-to-win mechanics
- **Accessible Design** - Easy to learn, with intuitive UI and helpful commands
- **Customizable Experience** - Server admins can tailor settings to their community
- **Admin-Friendly** - Interactive setup wizard and comprehensive management tools
- **Optimized Performance** - Efficient database structure and storage management

---

## ✨ Features

<details open>
<summary><b>🦄 Creature System</b></summary>
<br>

- **300+ Unique Veramons** with detailed stats, types, and abilities
- **Shiny Variants** with distinctive appearances and enhanced stats
- **Multiple Evolution Paths** based on various conditions
- **Special Forms** that modify appearances and abilities
- **Rarity Tiers** from common to legendary, each with unique traits

</details>

<details>
<summary><b>🗺️ Exploration System</b></summary>
<br>

- **Diverse Biomes** with unique Veramon populations
- **Dynamic Weather** affecting spawns and battle effectiveness
- **Day/Night Cycle** with time-specific encounters
- **Special Locations** unlocked through progression
- **Advanced Spawn Algorithm** balancing rarity and discovery

</details>

<details>
<summary><b>⚔️ Battle System</b></summary>
<br>

- **Strategic Turn-Based Combat** with abilities and type advantages
- **Actor-Based Architecture** providing stability and performance
- **Resilient Persistence System** allowing battles to survive bot restarts
- **PvP Battles** against other trainers
- **PvE Challenges** against themed NPC trainers
- **Multi-Battle Support** for 2v2 team battles
- **Interactive Battle UI** with move selection and real-time feedback
- **Type Effectiveness** creating strategic depth
- **Advanced Status Effects** with unique durations and interactions
- **Optimized Performance** with intelligent caching and metrics tracking
- **Battle Rewards** including XP, tokens, and evolution opportunities

</details>

<details>
<summary><b>💰 Economy & Shops</b></summary>
<br>

- **Token-Based Economy** balancing income and expenditure
- **Daily Rewards** with streak bonuses
- **Multiple Shops** for different items and upgrades
- **Consumable Items** providing temporary boosts
- **Equipment** for permanent improvements
- **Quest Rewards** tied to gameplay accomplishments
- **Item Trading** between players

</details>

<details>
<summary><b>🤝 Social Systems</b></summary>
<br>

- **Guild System** - Small parties (5 players) for casual cooperative play
- **Faction System** - Large organizations (50+ players) with:
  - Hierarchical ranks and customizable permissions
  - Treasury for collective purchasing power
  - Faction-exclusive shops with level-based items
  - Territory control for resource bonuses
  - Faction wars for server domination
  - Temporary buffs benefiting all faction members
  - Contribution tracking and leaderboards
- **Trading System** - Safe exchange of Veramon and items
- **Leaderboards** - Competitive rankings across multiple categories

</details>

<details>
<summary><b>✅ Quest & Achievement System</b></summary>
<br>

- **Daily & Weekly Quests** refreshing regularly
- **Achievement System** with permanent rewards
- **Story Quests** advancing the game narrative
- **Special Event Quests** during limited-time events
- **Quest Chains** with progressive difficulty and rewards

</details>

<details>
<summary><b>🎭 Events & Tournaments</b></summary>
<br>

- **Seasonal Events** with themed content and rewards
- **Community Challenges** with collaborative goals
- **PvP Tournaments** with brackets and prizes
- **Special Spawns** during event periods
- **Limited-Time Items** available only during events

</details>

<details>
<summary><b>🛠️ Customization & Settings</b></summary>
<br>

- **Profile Customization** to personalize your trainer
- **UI Theming** options for visual preferences
- **Notification Settings** for controlling bot messages
- **Accessibility Options** ensuring all players can enjoy
- **Server-Wide Settings** for admin customization

</details>

<details>
<summary><b>💎 VIP Benefits</b></summary>
<br>

- **Cosmetic Perks** for visual customization
- **Quality-of-Life Features** without gameplay advantage
- **Exclusive Profile Themes** and visual effects
- **DM Support** for playing in private messages
- **Expanded Storage** for collections management

</details>

---

## 🔮 Commands

All commands use Discord's slash command system for easy discovery and usage.

<details>
<summary><b>🔍 Core Commands</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | View available commands | `/help` |
| `/start` | Begin your adventure | `/start` |
| `/daily` | Claim daily rewards | `/daily` |
| `/profile` | View your trainer profile | `/profile` |
| `/settings` | Configure your personal settings | `/settings` |

</details>

<details>
<summary><b>🦄 Veramon Collection</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/list` | View your captured Veramon | `/list` |
| `/info [veramon_id]` | View details about a specific Veramon | `/info v12345` |
| `/nickname [veramon_id] [name]` | Change a Veramon's nickname | `/nickname v12345 Sparkles` |
| `/release [veramon_id]` | Release a captured Veramon | `/release v12345` |
| `/active_list` | View your active Veramon team | `/active_list` |
| `/active_add [veramon_id]` | Add a Veramon to your active team | `/active_add v12345` |
| `/active_remove [veramon_id]` | Remove a Veramon from your active team | `/active_remove v12345` |

</details>

<details>
<summary><b>🗺️ Exploration</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/explore` | Explore for wild Veramon | `/explore` |
| `/explore [biome]` | Explore a specific biome | `/explore forest` |
| `/catch [veramon_id]` | Attempt to catch a wild Veramon | `/catch w12345` |
| `/biomes` | View available biomes | `/biomes` |
| `/weather` | Check current weather conditions | `/weather` |

</details>

<details>
<summary><b>⚔️ Battle System</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/battle_pve [difficulty]` | Battle an NPC trainer | `/battle_pve normal` |
| `/battle_pvp [player]` | Challenge another player | `/battle_pvp @Username` |
| `/battle_multi [type] [team_size]` | Start a multi-player battle | `/battle_multi 2v2 2` |
| `/move [move_id]` | Use a move in battle | `/move tackle` |
| `/switch [veramon_id]` | Switch active Veramon in battle | `/switch v12345` |

</details>

<details>
<summary><b>💰 Economy & Shopping</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/balance` | Check your token balance | `/balance` |
| `/shop` | Browse the item shop | `/shop` |
| `/shop [category]` | Browse a specific shop category | `/shop boosts` |
| `/shop_buy [item_id] [quantity]` | Purchase an item | `/shop_buy token_magnet 1` |
| `/inventory` | View your items | `/inventory` |
| `/use [item_id] [target]` | Use an item | `/use potion v12345` |

</details>

<details>
<summary><b>🤝 Social & Guilds</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/guild_create [name]` | Create a new guild | `/guild_create PokeExplorers` |
| `/guild_join [guild_id]` | Join an existing guild | `/guild_join g12345` |
| `/guild_leave` | Leave your current guild | `/guild_leave` |
| `/guild_info [guild_id]` | View guild details | `/guild_info g12345` |
| `/guild_invite [player]` | Invite a player to your guild | `/guild_invite @Username` |
| `/leaderboard [category]` | View leaderboards | `/leaderboard catches` |

</details>

<details>
<summary><b>⚡ Faction System</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/faction_create [name]` | Create a new faction (Admin only) | `/faction_create Mystic` |
| `/faction_join [faction_name]` | Request to join a faction | `/faction_join Mystic` |
| `/faction_info [faction_name]` | View faction details | `/faction_info Mystic` |
| `/faction_leave` | Leave your current faction | `/faction_leave` |
| `/faction_upgrade [upgrade_name]` | Purchase faction upgrades | `/faction_upgrade token_economy` |
| `/faction_buff [buff_type]` | Activate faction-wide buffs | `/faction_buff token` |
| `/faction_war [target_faction]` | Declare war on another faction | `/faction_war Valor` |
| `/faction_shop` | Browse faction-specific shop | `/faction_shop` |
| `/faction_shop_buy [item_id] [quantity]` | Purchase from faction shop | `/faction_shop_buy faction_token_booster 1` |
| `/faction_level` | Check faction level and progress | `/faction_level` |
| `/faction_contribute [amount]` | Donate tokens to faction treasury | `/faction_contribute 1000` |
| `/faction_contributions` | View top faction contributors | `/faction_contributions` |
| `/faction_buffs` | View active faction buffs | `/faction_buffs` |

</details>

<details>
<summary><b>💎 VIP Commands</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/vip_shop` | Browse VIP-exclusive shop | `/vip_shop` |
| `/vip_shop_buy [item_id] [quantity]` | Purchase from VIP shop | `/vip_shop_buy premium_token_pack 1` |
| `/daily_vip` | Claim enhanced VIP daily rewards | `/daily_vip` |
| `/nickname_color [color]` | Change nickname color in bot embeds | `/nickname_color #FF5500` |

</details>

<details>
<summary><b>🛡️ Moderation Commands</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/mod_trade_view [trade_id]` | View details of any trade | `/mod_trade_view t12345` |
| `/mod_trade_cancel [trade_id] [reason]` | Cancel a suspicious trade | `/mod_trade_cancel t12345 Suspicious activity` |
| `/mod_warn [user] [reason]` | Issue a warning to a user | `/mod_warn @Username Spamming` |
| `/mod_mute [user] [duration] [reason]` | Temporarily mute a user | `/mod_mute @Username 1h Inappropriate behavior` |
| `/mod_ban [user] [reason]` | Ban a user from using the bot | `/mod_ban @Username Cheating` |
| `/mod_logs [user]` | View moderation logs for a user | `/mod_logs @Username` |

</details>

<details>
<summary><b>⚙️ Admin Commands</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/admin_config [setting] [value]` | Configure bot settings | `/admin_config catch_rate 0.3` |
| `/admin_give_veramon [user] [veramon_id]` | Give a Veramon to a user | `/admin_give_veramon @Username charizard` |
| `/admin_give_tokens [user] [amount]` | Give tokens to a user | `/admin_give_tokens @Username 1000` |
| `/admin_spawn_rate [biome] [rarity] [percentage]` | Adjust spawn rates | `/admin_spawn_rate forest legendary 0.01` |
| `/setup` | Interactive bot configuration wizard | `/setup` |
| `/db_backup` | Create database backups | `/db_backup` |
| `/db_restore` | Restore from backups | `/db_restore` |

</details>

<details>
<summary><b>🔒 Permission Levels and Commands</b></summary>
<br>

Veramon Reunited has 5 permission levels, each with access to different commands:

#### USER Level
Basic gameplay access for all players:
- `/explore` - Explore biomes for wild Veramon
- `/catch` - Attempt to catch a wild Veramon
- `/battle_wild` - Battle wild Veramon
- `/profile` - View your trainer profile
- `/balance` - Check your token balance
- `/shop` - Browse the item shop
- `/shop_buy` - Purchase items from the shop
- `/transfer` - Transfer tokens to another player
- `/inventory` - View your items
- `/collection` - View your Veramon collection
- `/veramon_details` - Check details of a Veramon
- `/nickname` - Set a nickname for your Veramon
- `/guild_join` - Join an existing guild

#### VIP Level
Enhanced gameplay experience with bonuses:
- All USER level commands
- `/daily_bonus` - Claim enhanced daily rewards
- `/set_profile_theme` - Customize profile appearance
- `/set_title` - Set a special title for your profile
- Access to exclusive VIP shop items
- Reduced spawn cooldowns (15s vs 30s)
- Increased catch rates (+10% bonus)
- Enhanced shiny rates (+20% bonus)
- Increased XP gain (+25% bonus)

#### MOD Level
Moderation capabilities for server moderators:
- All VIP level commands
- `/view_logs` - Access system and user logs
- `/cancel_trade` - Cancel other users' trades
- `/moderate` - Moderate faction/guild chat
- `/temp_ban` - Issue temporary bans
- `/lookup_user` - View detailed user information
- `/reset_cooldown` - Reset a user's cooldowns
- `/view_reports` - Monitor user reports

#### ADMIN Level
Server management powers for administrators:
- All MOD level commands
- `/setup` - Interactive bot configuration wizard
- `/award` - Award tokens to users
- `/event` - Create and manage events
- `/config_spawns` - Configure spawn rates
- `/override_price` - Override shop prices
- `/modify_inventory` - Manage user inventories
- `/delete_capture` - Delete captures
- `/spawn_veramon` - Spawn any Veramon
- `/manage_guild` - Guild management commands
- `/manage_faction` - Faction management commands
- `/db_backup` - Create database backups
- `/db_restore` - Restore from backups

#### DEV Level
Complete system control for developers:
- All ADMIN level commands
- `/create_veramon` - Create/modify Veramon
- `/system_stats` - View system diagnostics
- `/update_config` - Update bot configuration
- `/debug_logs` - Access debug logs
- `/reload` - Reload bot modules
- `/query` - Execute custom database queries
- `/db_analyze` - Analyze database usage
- `/setup_reset` - Reset all bot configuration

</details>

<details>
<summary><b>🫂 Social & Profiles</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/profile [user]` | View your or another player's profile | `/profile @Username` |
| `/leaderboard [category] [timeframe]` | View game leaderboards | `/leaderboard tokens all` |
| `/guild_create [name]` | Create a new guild | `/guild_create PokeExplorers` |
| `/guild_join [guild_id]` | Join an existing guild | `/guild_join g12345` |
| `/guild_leave` | Leave your current guild | `/guild_leave` |
| `/guild_info [guild_id]` | View guild details | `/guild_info g12345` |
| `/friend [action] [user]` | Manage your friends list | `/friend add @Username` |

</details>

<details>
<summary><b>💸 Economy & Tokens</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/shop` | Browse the item shop | `/shop` |
| `/shop_buy [item_id] [quantity]` | Purchase items from the shop | `/shop_buy ultra_ball 5` |
| `/transfer [user] [amount] [message]` | Transfer tokens to another player | `/transfer @Username 100 Thanks for the trade!` |
| `/transaction_history [type] [limit]` | View your token transaction history | `/transaction_history all 10` |
| `/inventory` | View your items | `/inventory` |
| `/daily` | Claim daily tokens and rewards | `/daily` |
| `/faction_shop` | Browse the faction shop | `/faction_shop` |
| `/faction_shop_buy [item_id] [quantity]` | Purchase from faction shop | `/faction_shop_buy faction_token_booster 1` |
| `/faction_contribute [amount]` | Donate tokens to faction treasury | `/faction_contribute 1000` |

</details>

<details>
<summary><b>🏆 Team Management</b></summary>
<br>

| Command | Description | Example |
|---------|-------------|---------|
| `/team [action] [team_name]` | Create, view, or manage teams | `/team create MyEliteTeam` |
| `/team_add [team_name] [capture_id] [position]` | Add a Veramon to a team | `/team_add MyEliteTeam 12345 1` |
| `/team_remove [team_name] [position]` | Remove a Veramon from a team | `/team_remove MyEliteTeam 2` |
| `/team_rename [team_name] [new_name]` | Rename an existing team | `/team_rename MyEliteTeam ChampionSquad` |
| `/battle_pvp [user] [team_name]` | Challenge a player with a specific team | `/battle_pvp @Username MyEliteTeam` |

</details>

---

## 🚀 Setup Guide

### Adding to Your Server

1. **[Click Here to Invite the Bot](https://discord.com/)**
2. Select the server you wish to add Veramon Reunited to
3. Authorize the required permissions
4. The bot will join your server ready to use!

### Quick Setup

1. Run the interactive setup wizard with `/setup`
2. Follow the step-by-step prompts to configure:
   - General settings (bot prefix, status, timezone)
   - Game features (battles, trading, quests, events)
   - Economy settings (token rewards, starting balances)
   - Spawn settings (rates, rarities, biomes)
   - Channel configurations (for spawns, announcements, logs)
   - Role assignments (admin, moderator, VIP)
   - Security settings (rate limits, cooldowns)
3. Your configuration changes are saved automatically

### Manual Setup

If you prefer a more hands-on approach, you can also set up the bot manually:

1. Create these recommended roles (optional but encouraged):
   - **Veramon Trainer** - For regular users
   - **VIP** - For premium users or supporters
   - **Mod** - For server moderators
   - **Admin** - For server administrators
   - **Dev** - For bot developers
2. Start with basic commands:
   - `/help` - View available commands
   - `/start` - Begin your adventure
   - `/explore` - Find your first Veramon

### Server Configuration

Server administrators can customize the bot experience:

1. Use `/admin_config` to adjust:
   - Spawn rates and catch difficulties
   - Economy balance
   - Feature availability
   - Channel restrictions

2. Set up dedicated channels (recommended):
   - `#veramon-catching` - For exploration and catching
   - `#veramon-battles` - For trainer battles
   - `#veramon-trading` - For trading marketplace
   - `#veramon-announcements` - For bot announcements

---

## 🧩 Developer Guide

### Project Structure

The Veramon Reunited codebase is organized for maintainability and separation of concerns:

```
veramon_reunited/
├── README.md             # Project documentation
├── main.py               # Bot entry point
├── src/                  # Source code
│   ├── bot.py            # Core Discord bot configuration
│   ├── cogs/             # Discord command modules 
│   │   ├── admin/        # Administrative commands
│   │   ├── gameplay/     # Core gameplay commands
│   │   └── social/       # Community interaction commands
│   ├── models/           # Data models
│   │   ├── battle.py     # Battle mechanics
│   │   ├── battle_actor.py # Actor-based battle implementation
│   │   ├── battle_manager.py # Battle actor management
│   │   ├── permissions.py # Permission system
│   │   └── veramon.py    # Creature system
│   ├── utils/            # Utility functions
│   │   ├── actor_system.py # Actor-based architecture
│   │   ├── battle_metrics.py # Battle performance tracking
│   │   ├── cache_manager.py # Caching mechanisms
│   │   ├── data_loader.py # JSON data loading
│   │   ├── performance_monitor.py # System metrics
│   │   └── ui_helpers.py # Discord UI utilities
│   └── db/               # Database management
│       ├── db.py         # Database connection
│       ├── schema.py     # Schema definition
│       └── cache_manager.py # Query caching
└── data/                 # Game data (JSON)
    ├── veramon/          # Creature definitions
    ├── moves/            # Ability definitions
    └── items/            # Item definitions
```

### Key Technologies

- **discord.py** - Python library for Discord API interaction
- **Discord UI Components** - Buttons, selects, and modals for interactive gameplay
- **SQLite** - Local database storage for user data and game state
- **JSON** - Data storage for game assets
- **Actor System** - Battle state management architecture

### Core Systems

#### Discord Integration

The bot is built entirely around Discord's interface capabilities:

- **Slash Commands** - All user interactions start with / commands
- **Button Interactions** - Battle controls, team management, and navigation
- **Embeds** - Rich visual displays for battles, profiles, and game information
- **Ephemeral Messages** - Private responses for sensitive information
- **Component Interactions** - Selection menus, modals for user input

#### Actor-Based Architecture

The battle system utilizes an actor-based architecture, providing:

- **Isolation** - Each battle runs in its own isolated context
- **Persistence** - Battles persist through bot restarts
- **Discord Compatibility** - Designed to handle Discord's interaction timeouts
- **Resilience** - Error handling and graceful recovery

```python
# Example of Discord command calling the actor system
@app_commands.command(name="battle_move", description="Execute a move in battle")
async def battle_move(self, interaction: discord.Interaction, move_name: str):
    # Defer the response to avoid Discord timeout
    await interaction.response.defer(ephemeral=True)
    
    battle_id = self.get_user_battle(str(interaction.user.id))
    if not battle_id:
        return await interaction.followup.send("You're not in a battle!")
    
    # Get the battle actor through the manager
    battle_ref = self.battle_manager.get_battle(battle_id)
    
    # Send a message to the actor and await response
    result = await battle_ref.ask({
        "action": "execute_move",
        "user_id": str(interaction.user.id),
        "move_name": move_name
    })
    
    # Send the result back to Discord
    await interaction.followup.send(result["message"])
```

#### Battle Metrics and Performance

The system includes comprehensive performance monitoring for Discord interactions:

- **Command Timing** - Track execution time of slash commands
- **Response Times** - Monitor time to respond to user interactions
- **API Rate Limits** - Monitor and prevent Discord API rate limiting
- **Memory Usage** - Track memory consumption to ensure stability

### Local Development Setup

1. **Prerequisites**
   - Python 3.10+ installed
   - Git for version control
   - A Discord Developer account and bot application

2. **Clone the repository**
   ```bash
   git clone https://github.com/killerdash117/veramon-reunited.git
   cd veramon-reunited
   ```

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up your .env file**
   ```env
   BOT_TOKEN=your_discord_bot_token
   COMMAND_PREFIX=!
   DB_PATH=sqlite:///database.sqlite
   LOG_LEVEL=INFO
   DEVELOPER_IDS=comma,separated,discord,ids
   ```

6. **Run the bot**
   ```bash
   python src/main.py
   ```

### Common Development Tasks

#### Adding a New Veramon

Create a new JSON file in `data/veramon/`:

```json
{
  "dex_id": 301,
  "name": "Flamefox",
  "type": ["fire"],
  "base_stats": {
    "hp": 45,
    "attack": 60,
    "defense": 40,
    "sp_attack": 70,
    "sp_defense": 50,
    "speed": 65
  },
  "moves": ["ember", "tackle", "fire_spin", "quick_attack"],
  "evolution": {
    "evolves_to": "Blazitar",
    "level_required": 16
  },
  "rarity": "uncommon",
  "flavor_text": "A newly discovered fire-type that lives in volcanic areas."
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
| `trading` & `trading_items` | Trading system |
| `battle_history` | Record of battles |
| `quests` & `user_quests` | Quest system |

---

## 🤝 Contributing

We welcome contributions to Veramon Reunited! Here's how to get involved:

### Ways to Contribute

- **Bug Reports**: Open an issue on our GitHub repo
- **Feature Requests**: Suggest new features or improvements
- **Code Contributions**: Submit pull requests with new features or fixes
- **Documentation**: Help improve our docs and guides
- **Testing**: Try new features and provide feedback

### Contribution Guidelines

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Commit with clear messages**
   ```bash
   git commit -m "Add: Amazing new feature that does X"
   ```
5. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Development Standards

- Follow PEP 8 style guidelines
- Include docstrings for all functions, classes, and modules
- Write tests for new functionality
- Update documentation to reflect changes
- Keep performance in mind for all changes

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

## 🌟 Join the Community 🌟

[Discord Server](https://discord.gg/) • [GitHub Repository](https://github.com/killerdash117/veramon-reunited) • [Support the Project](https://github.com/sponsors/killerdash117)

*Created with ❤️ by [Killerdash117](https://github.com/killerdash117)*

</div>
