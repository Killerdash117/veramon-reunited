<div align="center">

# 🌟 Veramon Reunited 🌟

<img src="https://i.imgur.com/EMNMEsp.jpeg" alt="Veramon Reunited" width="500"/>

[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://github.com/killerdash117/veramon-reunited/blob/master/LICENSE)
[![Version](https://img.shields.io/badge/Version-0.44.0-brightgreen.svg?style=flat-square)](https://github.com/killerdash117/veramon-reunited/releases)
[![Discord](https://img.shields.io/badge/Discord-Coming%20Soon-7289DA?logo=discord&logoColor=white&style=flat-square)](https://github.com/killerdash117/veramon-reunited)

**A comprehensive Discord bot for monster-catching adventures in your server**

[Features](#-features) • [Commands](#-commands) • [Rank-Specific Commands](#-rank-specific-commands) • [Setup Guide](#-setup-guide) • [Getting Started](#-getting-started) • [Project Structure](#-project-structure) • [Contributing](#-contributing) • [Troubleshooting](#-troubleshooting)

</div>

---

<details open>
<summary><h2 id="-features"> 🎮 Features</h2></summary>

<details open>
<summary><h3 id="-creature-system"> 🦖 Creature System</h3></summary>

- **Diverse Veramon Collection** with unique stats, types, and abilities
  - Creatures spanning multiple elemental types and rarities
  - Distinct evolution lines with branching paths
  - Individual stats that affect battle performance
- **Shiny Variants** with distinctive appearances and enhanced stats
  - Rare color variations with boosted attributes
  - Collectible for completionists and competitive players
- **Evolution System** with level-based triggers
  - Creatures evolve at specific level thresholds
  - Evolution improves base stats and may change typing
- **Type-Based Mechanics** with strengths and weaknesses
  - Strategic type matchups creating a depth of gameplay
  - Dual-typing available for certain creatures
- **Move Learning** based on Veramon level and type
  - New abilities unlocked as Veramon grow stronger
  - Type-specific move sets for strategic diversity
- **Capture System** with rarity-based catch rates
  - Different catch rates based on creature rarity
  - Special items to boost capture success
- **Collection Management** with sorting and filtering options
  - Organize Veramon by level, type, rarity, and more
  - Filter to quickly find specific Veramon
- **Customizable Nicknames** for personalization
  - Make your Veramon collection uniquely yours
  - Display nicknames in battles and trades

</details>

<details open>
<summary><h3 id="-battle-system"> ⚔️ Battle System</h3></summary>

- **PvE Battles** against NPC trainers with varying difficulties
- **PvP Battles** between players with full move selection
- **Turn-Based Combat** with strategic depth
- **Team Management** with up to 6 Veramon per team
- **Move Selection** with type-based effectiveness
- **Status Effects** that impact battle performance
- **Battle Rewards** including XP, tokens, and evolution opportunities
- **Enhanced Battle UI** with interactive buttons for move selection

</details>

<details open>
<summary><h3 id="-trading-system"> 🔄 Trading System</h3></summary>

- **Secure Player-to-Player Trading** with confirmation safeguards
- **Complete Trade Commands** for creating, managing, and viewing trades
- **Veramon Trading** with preview of stats and abilities
- **Trade Verification** requiring approval from both parties
- **Trade History** for tracking past exchanges
- **Trade Notifications** for pending and completed trades
- **Safety Features** to prevent scams and ensure fair trades

</details>

<details open>
<summary><h3 id="-faction-system"> ⚔️ Faction System</h3></summary>

- **Faction Selection** choose your allegiance among competing groups
  - Join server-wide factions with unique themes and benefits
  - Climb the ranks from Recruit to Leader based on contribution
  - Receive faction-specific bonuses to catching and battles
- **Advanced Rank System**
  - Hierarchical ranks with customizable permissions
  - Leadership opportunities with treasury and member management
  - Rank-based ability unlocks for progression motivation
- **Territory Control**
  - Capture and defend strategic locations across biomes
  - Earn passive bonuses from controlled territories
  - Special Veramon spawns in faction-controlled areas
- **Faction Wars**
  - Declare war on rival factions to capture territories
  - Participate in PvP and PvE challenges to earn war points
  - Win rewards and fame for your faction through victory
- **Faction Treasury**
  - Shared economy with group funding for upgrades
  - Contribute resources to unlock faction-wide benefits
  - Fund wars, territory claims, and special events
- **Faction Buffs & Upgrades**
  - Temporary buffs for catch rates, XP, battle advantages
  - Permanent upgrades that grow your faction's power
  - Stack bonuses for maximum efficiency
- **Faction Challenges**
  - Complete tasks to earn points for your faction
  - Daily and weekly challenges for active participation
  - Special rewards for top-performing factions

</details>

<details open>
<summary><h3 id="-exploration-system"> 🗺️ Exploration System</h3></summary>

- **Multiple Biomes** each with different Veramon spawns
- **Rarity Tiers** affecting encounter rates
- **Time-Based Spawns** with day/night variations
- **Special Events** with limited-time creatures
- **Encounter Boosts** through items and upgrades
- **Location-Based Exploration** with biome-specific mechanics

</details>

<details>
<summary><h3 id="-social-systems"> 👥 Social Features</h3></summary>

- **Friend System** for connecting with other players
- **Guild System** for team-based gameplay
- **Leaderboards** tracking various achievements
- **Profiles** showing player stats and accomplishments
- **Team Sharing** to showcase your best Veramon teams

</details>

<details>
<summary><h3 id="-ui-components"> 🖌️ UI Components</h3></summary>

- **Interactive Buttons** for intuitive gameplay
- **Dropdown Menus** for selection options
- **Customizable Themes** for personalized experience
- **Responsive Design** that works on all devices
- **UI Integration** with all major game systems

</details>

<details>
<summary><h3 id="-accessibility"> ♿ Accessibility Features</h3></summary>

- **Comprehensive Settings Panel** with multiple accessibility options
- **Text Size Options** for readability
- **Color Vision Deficiency Support** with specialized modes
- **High Contrast Mode** for enhanced visibility
- **Extended Interaction Timeouts** for users who need more time
- **Simplified UI Mode** for reduced visual complexity

</details>

</details>

---

<details>
<summary><h2 id="-commands"> 📚 Commands</h2></summary>

<details>
<summary><h3>Getting Started</h3></summary>

| Command | Description | Example |
|---------|-------------|---------| 
| `/help` | View available commands | `/help` |
| `/help [category]` | View commands in a specific category | `/help battle` |
| `/start` | Begin your Veramon adventure | `/start` |
| `/tutorial` | Interactive guide to gameplay | `/tutorial` |
| `/settings` | Adjust your user settings | `/settings` |
| `/collection` | View your Veramon collection | `/collection` |

</details>

<details>
<summary><h3>Veramon Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------| 
| `/collection` | View your Veramon collection | `/collection` |
| `/veramon_info [id]` | View details about a specific Veramon | `/veramon_info v12345` |
| `/evolve [id]` | Evolve an eligible Veramon | `/evolve v12345` |
| `/rename [id] [name]` | Rename a Veramon | `/rename v12345 Sparky` |
| `/favorite [id]` | Add/remove a Veramon from favorites | `/favorite v12345` |
| `/release [id]` | Release a Veramon | `/release v12345` |
| `/sort [method]` | Sort your collection | `/sort newest` |
| `/filter [types]` | Filter your collection | `/filter fire,water` |

</details>

<details>
<summary><h3>Battle Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------| 
| `/battle [player]` | Challenge a player to battle | `/battle @Username` |
| `/battle_npc [difficulty]` | Battle an NPC trainer | `/battle_npc expert` |
| `/battle_accept` | Accept a battle challenge | `/battle_accept` |
| `/battle_decline` | Decline a battle challenge | `/battle_decline` |
| `/move [move_name]` | Use a move in battle | `/move Fireball` |
| `/switch [veramon_id]` | Switch active Veramon in battle | `/switch v12345` |
| `/battle_info` | View current battle status | `/battle_info` |
| `/battle_log` | View your battle history | `/battle_log` |
| `/team_create [name]` | Create a new battle team | `/team_create Dragons` |
| `/team_add [team] [id] [position]` | Add Veramon to team | `/team_add Dragons v12345 1` |
| `/team_remove [team] [position]` | Remove Veramon from team | `/team_remove Dragons 1` |
| `/team_list` | View your battle teams | `/team_list` |
| `/team_view [name]` | View a specific team | `/team_view Dragons` |

</details>

<details>
<summary><h3>Economy & Shopping</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/balance` | Check your token balance | `/balance` |
| `/shop` | Browse the item shop | `/shop` |
| `/buy [item] [quantity]` | Purchase an item | `/buy pokeball 5` |
| `/inventory` | View your items | `/inventory` |
| `/use [item] [target]` | Use an item | `/use rare_candy v12345` |
| `/sell [item] [quantity]` | Sell an item | `/sell greatball 3` |
| `/daily` | Claim daily rewards | `/daily` |
| `/token_exchange [amount]` | Exchange special tokens | `/token_exchange 500` |

</details>

<details>
<summary><h3>Exploration Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/explore [biome]` | Explore a specific biome | `/explore forest` |
| `/biomes` | View available biomes | `/biomes` |
| `/catch` | Attempt to catch the active Veramon | `/catch` |
| `/run` | Flee from an encounter | `/run` |
| `/use_bait` | Use bait to increase catch chance | `/use_bait` |
| `/catch_history` | View recent catches | `/catch_history` |
| `/set_favorite_biome [biome]` | Set a preferred biome | `/set_favorite_biome mountain` |

</details>

<details>
<summary><h3>Social Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/profile [user]` | View your or another user's profile | `/profile @Username` |
| `/leaderboard [category]` | View server rankings | `/leaderboard shiny` |
| `/friend_add [player]` | Add a player to friends | `/friend_add @Username` |
| `/friend_remove [player]` | Remove a player from friends | `/friend_remove @Username` |
| `/friend_list` | View your friends list | `/friend_list` |
| `/guild_create [name]` | Create a new guild | `/guild_create DragonSlayers` |
| `/guild_invite [player]` | Invite player to your guild | `/guild_invite @Username` |
| `/guild_join [guild_id]` | Accept guild invitation | `/guild_join g12345` |
| `/guild_leave` | Leave your current guild | `/guild_leave` |
| `/guild_info [guild]` | View guild information | `/guild_info DragonSlayers` |

</details>

<details>
<summary><h3>Faction Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/faction_list` | View all available factions | `/faction_list` |
| `/faction_info [faction_name]` | View faction details | `/faction_info Mystic` |
| `/faction_join [faction_name]` | Join a faction | `/faction_join Valor` |
| `/faction_create [name] [desc] [motto] [color]` | Create a new faction (Admin) | `/faction_create Instinct "Electric types" "Trust your instincts" #FFCC00` |
| `/faction_upgrade [upgrade_name]` | Purchase a faction upgrade | `/faction_upgrade treasury_capacity` |
| `/faction_upgrades` | View available faction upgrades | `/faction_upgrades` |
| `/faction_buff [buff_type] [duration]` | Activate a faction-wide buff | `/faction_buff xp 24` |
| `/faction_buffs` | View active faction buffs | `/faction_buffs` |
| `/faction_war [target_faction]` | Declare war on another faction | `/faction_war Valor` |
| `/faction_declare_war [target] [territory]` | Declare war over a territory | `/faction_declare_war 2 5` |
| `/faction_war_status` | Check status of active faction wars | `/faction_war_status` |
| `/faction_territories` | View all territories and ownership | `/faction_territories` |
| `/faction_claim_territory [territory_id]` | Claim an uncontrolled territory | `/faction_claim_territory 3` |

</details>

<details>
<summary><h3>Trading Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/trade_create [player]` | Start a trade with player | `/trade_create @Username` |
| `/trade_add [id]` | Add a Veramon to the trade | `/trade_add v12345` |
| `/trade_remove [id]` | Remove a Veramon from trade | `/trade_remove v12345` |
| `/trade_cancel` | Cancel your active trade | `/trade_cancel` |
| `/trade_list [status]` | View your trades | `/trade_list active` |
| `/trade_info [trade_id]` | View details of a trade | `/trade_info t12345` |
| `/trade_history [player]` | View trade history | `/trade_history @Username` |

</details>

<details>
<summary><h3>Settings Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/settings` | Open settings menu | `/settings` |
| `/theme [theme_name]` | Change your UI theme | `/theme dark` |
| `/theme_list` | View available themes | `/theme_list` |
| `/theme_preview [theme]` | Preview a theme | `/theme_preview neon` |
| `/accessibility` | Open accessibility menu | `/accessibility` |
| `/text_size [size]` | Change text size | `/text_size large` |
| `/notification_settings` | Manage notifications | `/notification_settings` |
| `/privacy [setting] [value]` | Update privacy settings | `/privacy profile friends_only` |

</details>

</details>

---

<details>
<summary><h2 id="-rank-specific-commands"> 🏅 Rank-Specific Commands</h2></summary>

<details>
<summary><h3>User Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/user_profile` | View your profile | `/user_profile` |
| `/user_settings` | Adjust your user settings | `/user_settings` |

</details>

<details>
<summary><h3>VIP Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/vip_daily_bonus` | Claim enhanced daily rewards | `/vip_daily_bonus` |
| `/vip_shiny_boost` | Activate increased shiny chance | `/vip_shiny_boost` |
| `/vip_premium_theme [theme]` | Apply exclusive UI themes | `/vip_premium_theme sunset` |
| `/vip_nickname_color` | Customize nickname colors | `/vip_nickname_color #FF5500` |
| `/vip_gift [user] [item]` | Gift items to other players | `/vip_gift @Username rare_candy` |

</details>

<details>
<summary><h3>Moderator Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/mod_warn [user_id] [reason]` | Issue a warning to a user | `/mod_warn @Username Breaking trade rules` |
| `/mod_mute [user_id] [duration] [reason]` | Temporarily mute a user from using commands | `/mod_mute @Username 60 Spamming commands` |
| `/mod_unmute [user_id]` | Remove a command mute from a user | `/mod_unmute @Username` |
| `/mod_trade_view [trade_id]` | View details of any trade | `/mod_trade_view 12345` |
| `/mod_trade_cancel [trade_id] [reason]` | Cancel a suspicious trade | `/mod_trade_cancel 12345 Potential scam` |
| `/mod_trade_history [user_id]` | View a user's trade history | `/mod_trade_history @Username` |
| `/mod_battle_view [battle_id]` | View details of any battle | `/mod_battle_view 12345` |
| `/mod_battle_end [battle_id] [winner_id]` | Force-end a stuck battle | `/mod_battle_end 12345 @Winner` |
| `/system_health` | Check the health of bot systems | `/system_health` |
| `/debug_info` | Generate a diagnostic report | `/debug_info` |

</details>

<details>
<summary><h3>Admin Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/admin_add_veramon [name] [types] [rarity]` | Add a new Veramon to the game | `/admin_add_veramon Fluffymon Fire,Flying rare` |
| `/admin_edit_veramon [name] [field] [value]` | Edit an existing Veramon's data | `/admin_edit_veramon Fluffymon type Water,Flying` |
| `/admin_add_ability [name] [details]` | Add a new ability to the game | `/admin_add_ability FireBlast Fire 80 0.85` |
| `/admin_give_veramon [player] [veramon]` | Give a Veramon to a player | `/admin_give_veramon @Username Fluffymon 15 true` |
| `/admin_spawn_rate [biome] [rarity] [percentage]` | Adjust spawn rates for a biome | `/admin_spawn_rate forest legendary 2.5` |
| `/admin_setup` | Run the interactive setup wizard | `/admin_setup` |
| `/admin_config [category]` | Configure bot settings | `/admin_config spawns` |
| `/admin_roles` | Configure role permissions | `/admin_roles` |
| `/admin_channels` | Configure channel settings | `/admin_channels` |
| `/admin_spawn` | Force spawn a Veramon | `/admin_spawn` |
| `/admin_event [event_id] [action]` | Manage server events | `/admin_event summer_fest start` |

</details>

<details>
<summary><h3>Developer Commands</h3></summary>

These commands are restricted to bot developers only (Dev rank) and are used for maintenance, debugging, and development purposes.

| Command | Description | Example |
|---------|-------------|---------|
| `/dev_debug [module]` | Enable debug mode for a module | `/dev_debug battle` |
| `/dev_error_log [count]` | View recent error logs | `/dev_error_log 5` |
| `/dev_memory_usage` | View memory usage statistics | `/dev_memory_usage` |
| `/dev_migration [version]` | Run database migrations | `/dev_migration 0.44.0` |
| `/dev_rebuild_indices` | Rebuild database indices | `/dev_rebuild_indices` |
| `/dev_test_data [amount]` | Generate test data | `/dev_test_data 10` |
| `/dev_reload [module]` | Reload a specific code module | `/dev_reload battle_cog` |
| `/dev_config [section] [key] [value]` | Modify configuration values | `/dev_config general spawn_rate 0.02` |
| `/dev_simulate_catch [rarity] [shiny_chance] [count]` | Simulate Veramon catches | `/dev_simulate_catch legendary 1.0 100` |
| `/dev_simulate_battle [team1] [team2] [iterations]` | Simulate battles between teams | `/dev_simulate_battle "Pyrox,Aquafin" "Leafy,Boltzap" 100` |

</details>

</details>

---

<details>
<summary><h2 id="-getting-started"> 🚀 Getting Started</h2></summary>

<details>
<summary><h3>Installation for Server Owners</h3></summary>

1. **Invite the Bot to Your Server**
   - Use [this invite link](https://github.com/killerdash117/veramon-reunited) to add Veramon Reunited to your server
   - Ensure it has the necessary permissions (Send Messages, Embed Links, Attach Files, etc.)

2. **Run Initial Setup**
   - Use the `/admin_setup` command to run the interactive setup wizard
   - Configure basic settings like spawn channels, admin roles, and game mechanics

3. **Configure Channels**
   - Designate channels for different activities:
     - Spawn channels where wild Veramon appear
     - Battle channels for PvP combat
     - Trading channels for exchanges
     - Announcement channels for events

4. **Set Up Roles**
   - Configure permission roles:
     - Admin role for full bot control
     - Moderator role for basic management
     - Dev role for developer access and debugging
     - VIP role for premium features (optional)

5. **Customize Settings**
   - Use `/admin_config` to fine-tune features
   - Adjust spawn rates, battle mechanics, and economy settings

6. **Start Playing!**
   - Have users run `/start` to begin their adventure
   - Use `/tutorial` for a guided introduction to features
</details>

<details>
<summary><h3>Installation for Bot Developers</h3></summary>

1. **Clone the Repository**
   ```bash
   git clone https://github.com/killerdash117/veramon-reunited.git
   cd veramon-reunited
   ```

2. **Set Up Environment**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Discord bot token
   ```

4. **Initialize Database**
   ```bash
   python src/tools/initialize_database.py
   ```

5. **Run the Bot**
   ```bash
   python src/main.py
   ```

6. **Optional: Development Tools**
   ```bash
   # Install development dependencies
   pip install -r requirements-dev.txt

   # Run tests
   pytest
   
   # Generate documentation
   sphinx-build -b html docs/source docs/build
   ```
</details>

<details>
<summary><h3>Quick Start for Players</h3></summary>

1. **Begin Your Journey**
   - Use `/start` to create your trainer profile
   - Get your first Veramon and basic supplies

2. **Learn the Basics**
   - Run `/tutorial` for an interactive guide
   - Use `/help` to see available commands

3. **Start Exploring**
   - Use `/explore` to look for wild Veramon in different biomes
   - Catch Veramon with `/catch` during encounters

4. **Build Your Team**
   - Create a battle team with `/team_create`
   - Add your best Veramon with `/team_add`

5. **Battle Other Players**
   - Challenge friends with `/battle`
   - Fight NPCs with `/battle_npc` to practice

6. **Trade and Socialize**
   - Start trades with `/trade_create`
   - Join a guild with `/guild_join` or create your own

7. **Collect Daily Rewards**
   - Use `/daily` to get free rewards
   - Build up a streak for better prizes
</details>

</details>

---

<details>
<summary><h2 id="-deployment"> 🚀 Deployment Options</h2></summary>

Veramon Reunited is designed to be deployed using Docker for reliable and consistent operation. There are two main approaches to deploying the bot:

<details>
<summary><h3>Option 1: Local Machine Deployment (Simple)</h3></summary>

This approach is perfect for individual server owners or developers who want a straightforward setup:

1. **Prerequisites**:
   - Docker and Docker Compose installed on your machine
   - A valid Discord bot token in your `.env` file

2. **Build and Run**:
   ```bash
   # Build and start in detached mode
   docker-compose -f docker/docker-compose.yml up -d
   
   # Check the logs
   docker-compose -f docker/docker-compose.yml logs -f
   
   # Stop the bot
   docker-compose -f docker/docker-compose.yml down
   
   # Restart after changes
   docker-compose -f docker/docker-compose.yml restart
   ```

3. **Benefits**:
   - Persistent data storage via volume mounts
   - Automatic restart if the bot crashes
   - Easy to update (just pull changes and restart)
   - Isolated environment for clean operation

4. **Updating**:
   ```bash
   git pull
   docker-compose -f docker/docker-compose.yml down
   docker-compose -f docker/docker-compose.yml up -d --build
   ```
</details>

<details>
<summary><h3>Option 2: CI/CD Pipeline (Advanced)</h3></summary>

For larger projects or teams that want automated deployments:

1. **Prerequisites**:
   - GitHub repository for your bot
   - A server (VPS) with Docker installed
   - DockerHub account (or other container registry)
   - Configured secrets in GitHub repository

2. **How It Works**:
   - Push changes to your main branch
   - GitHub Actions builds a Docker image
   - Image is pushed to DockerHub
   - Deployment server pulls the new image
   - Bot is automatically restarted with new version

3. **Setup**:
   - Configure GitHub secrets:
     - `DOCKERHUB_USERNAME`
     - `DOCKERHUB_TOKEN`
     - `SERVER_HOST`
     - `SERVER_USERNAME` 
     - `SERVER_KEY`
   - Ensure the `.github/workflows/deploy.yml` file is configured

4. **Benefits**:
   - Fully automated deployments
   - Test integration before deployment
   - Version control for releases
   - Multiple environment support (staging, production)
</details>

<details>
<summary><h3>Configuration Files</h3></summary>

The repository includes ready-to-use configuration files for both options:

- `docker/Dockerfile`: Defines the container build process
- `docker/docker-compose.yml`: Simplifies local deployment
- `.github/workflows/deploy.yml`: GitHub Actions workflow for CI/CD
- `.env.example`: Template for required environment variables

All Docker-related files are organized in the `docker` directory for cleaner project structure, while maintaining full support for the bot's enhanced battle system and trading functionality.
</details>

<details>
<summary><h3>Troubleshooting</h3></summary>

#### Common Issues

1. **Bot not starting:** Check the logs with `docker-compose -f docker/docker-compose.yml logs -f`
2. **Database errors:** Ensure the data directory has the correct permissions
3. **Missing environment variables:** Make sure all required variables are set in .env
4. **Discord connection issues:** Verify your bot token and internet connectivity

#### Container Health Check

The Docker container includes a health check that verifies connectivity to Discord. If the container is marked as unhealthy:

```bash
# Check container status
docker ps

# View detailed health check results
docker inspect --format='{{json .State.Health}}' veramon-bot | jq
```

#### Maintenance

**Database Backups**

The data directory is mounted as a volume, but it's recommended to set up regular backups:

```bash
# Manual backup
docker-compose -f docker/docker-compose.yml exec bot sh -c "sqlite3 /app/data/veramon_reunited.db .dump > /app/data/backups/backup_$(date +%Y%m%d).sql"
```

#### Security Considerations

- Never commit your `.env` file to version control
- Use a dedicated user with limited permissions for the bot
- Regularly update the base Docker image and dependencies
- Monitor the bot's resource usage to prevent potential DoS attacks
</details>

</details>

---

<details>
<summary><h2 id="-project-structure"> 🏗️ Project Structure</h2></summary>

```
veramon-reunited/
├── data/                  # Data storage
│   ├── database/          # SQLite database files
│   ├── backups/           # Database backups
│   └── static/            # Static assets and images
├── docs/                  # Documentation
│   ├── source/            # Documentation source files
│   └── build/             # Generated documentation
├── src/                   # Source code
│   ├── cogs/              # Discord command extensions
│   │   ├── admin/         # Administrative commands
│   │   ├── economy/       # Economy and shop systems
│   │   ├── gameplay/      # Core gameplay cogs
│   │   ├── settings/      # User settings
│   │   ├── social/        # Social features
│   │   └── user/          # General user commands
│   ├── database/          # Database management
│   ├── models/            # Data models
│   ├── ui/                # UI components
│   ├── utils/             # Utility functions
│   └── main.py            # Main entry point
├── tests/                 # Test suite
│   ├── functional/        # Functional tests
│   ├── integration/       # Integration tests
│   └── unit/              # Unit tests
├── docker/                # Docker configuration
│   ├── Dockerfile         # Container build process
│   └── docker-compose.yml # Local deployment configuration
├── .env.example           # Example environment variables
├── requirements.txt       # Dependencies
├── requirements-dev.txt   # Development dependencies
└── README.md              # This file
```

<details>
<summary><h3>Database Structure</h3></summary>

The bot uses SQLite for local database storage with the following main tables:

- **Users**: Player profiles and statistics
- **Veramon**: Creature definitions and attributes
- **Captures**: Player-owned Veramon instances
- **Teams**: Battle team configurations
- **Battles**: Battle history and results
- **Trades**: Trading history and records
- **Items**: Item definitions and effects
- **Inventories**: Player-owned items
- **Guilds**: Guild data and membership
- **Settings**: User and server settings

Tables include proper indices for performance and foreign key constraints for data integrity.
</details>

<details>
<summary><h3>Cog Organization</h3></summary>

Commands are organized into logical cogs:

- **AdminCog**: Server and bot administration
- **DeveloperCog**: Development tools and diagnostics
- **BattleCog**: Battle system and mechanics
- **TradingCog**: Trading functionality
- **CatchingCog**: Exploration and catching
- **EconomyCog**: Shop, items, and currency
- **TeamCog**: Team management
- **GuildCog**: Guild system
- **ProfileCog**: User profiles
- **SettingsCog**: User preferences
- **HelpCog**: Help documentation
</details>

</details>

---

<details>
<summary><h2 id="-contributing"> 🤝 Contributing</h2></summary>

We welcome contributions to Veramon Reunited! Here's how to get started:

<details>
<summary><h3>Contribution Guidelines</h3></summary>

1. **Fork the Repository**
   - Create your own fork of the project

2. **Create a Feature Branch**
   - Use a descriptive branch name (e.g., `feature/new-biome-system`)

3. **Follow Code Style**
   - Adhere to PEP 8 style guidelines
   - Run `flake8` to check your code

4. **Write Tests**
   - Add tests for new features
   - Ensure existing tests pass

5. **Document Your Changes**
   - Update relevant documentation
   - Add docstrings to new functions and classes

6. **Submit a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues

7. **Code Review**
   - Address feedback from maintainers
   - Make requested changes

8. **Continuous Integration**
   - Ensure all CI checks pass before merging
</details>

<details>
<summary><h3>Development Environment Setup</h3></summary>

1. **Clone Your Fork**
   ```bash
   git clone https://github.com/yourusername/veramon-reunited.git
   cd veramon-reunited
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Discord bot token
   ```

5. **Initialize Development Database**
   ```bash
   python src/tools/initialize_database.py --dev
   ```

6. **Run Tests**
   ```bash
   pytest
   ```
</details>

</details>

---

<details>
<summary><h2 id="-troubleshooting"> 🛠️ Troubleshooting</h2></summary>

<details>
<summary><h3>Common Issues</h3></summary>

#### Bot Not Responding
- Ensure your bot token is correct in .env
- Check Discord connection status
- Verify the bot has proper permissions in your server

#### Database Errors
- Run `python src/tools/fix_database_indices.py` to repair database
- Ensure SQLite is properly installed
- Check write permissions in the data directory

#### Battle System Problems
- Install required dependency: `pip install psutil`
- Check battle logs for errors: `/admin_logs battle_system`
- Restart battle service: `/admin_service restart battle_system`

#### Missing Veramon Data
- Run `python src/tools/fix_data_structure.py` to repair Veramon data
- Verify data files exist in the data directory
- Check JSON formatting in Veramon database files
</details>

<details>
<summary><h3>Error Codes</h3></summary>

| Code | Description | Solution |
|------|-------------|----------|
| E001 | Discord API Rate Limit | Wait a few minutes before trying again |
| E002 | Database Connection Failed | Check database file permissions |
| E003 | Veramon Data Missing | Run `python src/tools/fix_data_structure.py` |
| E004 | Battle System Error | Install psutil and restart the bot |
| E005 | Trading System Error | Check database indices and connectivity |
| E006 | Permission Error | Ensure bot has proper Discord permissions |
</details>

<details>
<summary><h3>Getting Help</h3></summary>

If you encounter issues not covered here:

1. Check the [Issues page](https://github.com/killerdash117/veramon-reunited/issues) for similar problems
2. Run `/debug_info` to generate a diagnostic report
3. Run `/system_health` to check the status of bot systems
4. *(Discord server coming soon)* - Community support will be available
5. Open a new issue with detailed information about the problem
</details>

</details>

---

<details>
<summary><h2 id="-contributors"> 👥 Contributors</h2></summary>

<div align="center">

### Core Team

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/killerdash117">
        <img src="https://github.com/killerdash117.png" width="100px;">
        <br>
        <sub><b>killerdash117</b></sub>
      </a>
      <br>
      <sub>Project Lead & Developer</sub>
    </td>
    <td align="center">
      <a href="https://github.com/Darkrell">
        <img src="https://github.com/Darkrell.png" width="100px;">
        <br>
        <sub><b>Darkrell</b></sub>
      </a>
      <br>
      <sub>Tester & Server Provider</sub>
    </td>
  </tr>
</table>

</div>

</details>

---

<div align="center">

## 📊 Project Status

[![Version](https://img.shields.io/badge/Version-0.44.0-brightgreen.svg?style=flat-square)](https://github.com/killerdash117/veramon-reunited/releases)
[![Last Updated](https://img.shields.io/badge/Last%20Updated-April%2022%2C%202025-blue.svg?style=flat-square)](https://github.com/killerdash117/veramon-reunited/commits)
[![Discord](https://img.shields.io/badge/Discord-Coming%20Soon-7289DA?logo=discord&logoColor=white&style=flat-square)](https://github.com/killerdash117/veramon-reunited)

### [Discord Server (Coming Soon)] | [Report Bugs](https://github.com/killerdash117/veramon-reunited/issues) | [Request Features](https://github.com/killerdash117/veramon-reunited/issues)

</div>

<div align="right">
<a href="#-veramon-reunited-">Back to Top ⬆️</a>
</div>
