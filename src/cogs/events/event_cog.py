import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

from src.models.event import Event, EventStatus, EventType
from src.models.event_manager import event_manager
from src.utils.ui_theme import theme_manager, ThemeColorType, create_themed_embed
from src.utils.interactive_components import NavigationView, MenuButton, PageTracker
from src.models.permissions import require_permission_level, PermissionLevel
from src.db.db import Database

logger = logging.getLogger('veramon.event')

class EventView(discord.ui.View):
    """Interactive view for event details and participation."""
    
    def __init__(self, user_id: str, event: Event, cog: 'EventCog', timeout: float = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.event = event
        self.cog = cog
        
        # Add buttons based on event status
        status = event.get_status()
        
        if status == EventStatus.ACTIVE:
            # Event is active, add participation buttons
            self.add_item(discord.ui.Button(
                label="View Quests",
                style=discord.ButtonStyle.primary,
                custom_id="view_quests"
            ))
            
            self.add_item(discord.ui.Button(
                label="Special Encounters",
                style=discord.ButtonStyle.success,
                custom_id="special_encounters"
            ))
            
            if event.special_items:
                self.add_item(discord.ui.Button(
                    label="Event Shop",
                    style=discord.ButtonStyle.secondary,
                    custom_id="event_shop"
                ))
                
            if event.community_goal:
                self.add_item(discord.ui.Button(
                    label="Community Goal",
                    style=discord.ButtonStyle.primary,
                    custom_id="community_goal"
                ))
        elif status == EventStatus.UPCOMING:
            # Event is upcoming, add reminder button
            self.add_item(discord.ui.Button(
                label="Set Reminder",
                style=discord.ButtonStyle.secondary,
                custom_id="set_reminder"
            ))
    
    @discord.ui.button(label="View Quests", style=discord.ButtonStyle.primary, custom_id="view_quests")
    async def view_quests(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View event-specific quests."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
            return
            
        await self.cog.show_event_quests(interaction, self.event.id)
    
    @discord.ui.button(label="Special Encounters", style=discord.ButtonStyle.success, custom_id="special_encounters")
    async def special_encounters(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View special encounters for this event."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
            return
            
        if not self.event.special_encounters:
            await interaction.response.send_message("This event has no special encounters.", ephemeral=True)
            return
            
        # Create embed for special encounters
        embed = create_themed_embed(
            self.user_id,
            title=f"{self.event.icon} {self.event.name} - Special Encounters",
            description="During this event, you can encounter these special Veramon:",
            color=self.event.theme_color
        )
        
        # Add each encounter
        for i, encounter in enumerate(self.event.special_encounters):
            name = encounter.get('name', 'Unknown')
            description = encounter.get('description', 'No description available')
            rarity = encounter.get('rarity', 'Common')
            location = encounter.get('location', 'Any location')
            
            encounter_text = f"**Rarity:** {rarity}\n"
            encounter_text += f"**Location:** {location}\n"
            encounter_text += description
            
            embed.add_field(
                name=f"{i+1}. {name}",
                value=encounter_text,
                inline=False
            )
            
        # Create view with exploration button
        view = discord.ui.View()
        
        @discord.ui.button(label="Start Exploring", style=discord.ButtonStyle.success)
        async def start_exploring(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != self.user_id:
                await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                return
                
            # Use the exploration command
            explore_command = self.cog.bot.get_command("explore")
            if explore_command:
                # This will redirect to the explore command
                await i.response.send_message(
                    "Starting exploration! Look for special event encounters.",
                    ephemeral=True
                )
                
                # This would normally invoke the explore command context
                # but since we're in an interaction, we need a workaround
                from src.cogs.exploration_cog import ExplorationCog
                exploration_cog = self.cog.bot.get_cog("ExplorationCog")
                
                if exploration_cog:
                    # Add the event_id to the exploration
                    await exploration_cog.explore(i, event_id=self.event.id)
                else:
                    await i.followup.send("Exploration feature is not available.", ephemeral=True)
            else:
                await i.response.send_message("Exploration feature is not available.", ephemeral=True)
        
        @discord.ui.button(label="Back to Event", style=discord.ButtonStyle.secondary)
        async def back_to_event(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != self.user_id:
                await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                return
                
            # Show the main event view
            embed = self.event.create_embed(self.user_id)
            await i.response.edit_message(embed=embed, view=self)
                
        # Add buttons
        view.add_item(start_exploring)
        view.add_item(back_to_event)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Event Shop", style=discord.ButtonStyle.secondary, custom_id="event_shop")
    async def event_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View and purchase event-specific items."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
            return
            
        if not self.event.special_items:
            await interaction.response.send_message("This event has no special items available.", ephemeral=True)
            return
            
        # Create embed for event shop
        embed = create_themed_embed(
            self.user_id,
            title=f"{self.event.icon} {self.event.name} - Event Shop",
            description="Limited-time items available during this event:",
            color=self.event.theme_color
        )
        
        # Get user's token balance
        db = self.cog.db
        result = await db.fetchone(
            "SELECT tokens FROM users WHERE user_id = ?",
            (self.user_id,)
        )
        token_balance = result['tokens'] if result else 0
        
        embed.add_field(name="Your Balance", value=f"{token_balance} tokens", inline=False)
        
        # Add each item
        for i, item in enumerate(self.event.special_items):
            name = item.get('name', 'Unknown')
            description = item.get('description', 'No description available')
            price = item.get('price', 100)
            item_id = item.get('id', f'event_{self.event.id}_item_{i}')
            
            item_text = f"**Price:** {price} tokens\n"
            item_text += description
            
            embed.add_field(
                name=f"{i+1}. {name}",
                value=item_text,
                inline=True
            )
            
        # Create view with purchase buttons
        view = discord.ui.View()
        
        # Add a select menu if more than 5 items
        if len(self.event.special_items) > 5:
            # Create a select menu
            select = discord.ui.Select(
                placeholder="Select an item to purchase",
                options=[
                    discord.ui.SelectOption(
                        label=item.get('name', f'Item {i+1}')[:100],
                        description=f"Price: {item.get('price', 100)} tokens"[:100],
                        value=str(i)
                    ) for i, item in enumerate(self.event.special_items)
                ]
            )
            
            async def select_callback(i: discord.Interaction):
                if str(i.user.id) != self.user_id:
                    await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                    return
                    
                # Get selected item
                item_index = int(select.values[0])
                item = self.event.special_items[item_index]
                
                # Try to purchase
                success, message = await self.cog.purchase_event_item(i, self.event.id, item)
                
                if success:
                    await i.response.send_message(message, ephemeral=True)
                else:
                    await i.response.send_message(message, ephemeral=True)
                
            select.callback = select_callback
            view.add_item(select)
        else:
            # Add button for each item if 5 or fewer
            for i, item in enumerate(self.event.special_items):
                name = item.get('name', f'Item {i+1}')
                price = item.get('price', 100)
                
                button = discord.ui.Button(
                    label=f"Buy {name} ({price} tokens)",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"buy_item_{i}"
                )
                
                async def make_callback(item_index):
                    async def callback(i: discord.Interaction, b: discord.ui.Button):
                        if str(i.user.id) != self.user_id:
                            await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                            return
                            
                        # Get selected item
                        item = self.event.special_items[item_index]
                        
                        # Try to purchase
                        success, message = await self.cog.purchase_event_item(i, self.event.id, item)
                        
                        if success:
                            await i.response.send_message(message, ephemeral=True)
                        else:
                            await i.response.send_message(message, ephemeral=True)
                    
                    return callback
                    
                button.callback = await make_callback(i)
                view.add_item(button)
        
        @discord.ui.button(label="Back to Event", style=discord.ButtonStyle.secondary)
        async def back_to_event(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != self.user_id:
                await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                return
                
            # Show the main event view
            embed = self.event.create_embed(self.user_id)
            await i.response.edit_message(embed=embed, view=self)
                
        # Add back button
        view.add_item(back_to_event)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Community Goal", style=discord.ButtonStyle.primary, custom_id="community_goal")
    async def community_goal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View community goal progress and details."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
            return
            
        if not self.event.community_goal:
            await interaction.response.send_message("This event has no community goal.", ephemeral=True)
            return
            
        # Create embed for community goal
        embed = create_themed_embed(
            self.user_id,
            title=f"{self.event.icon} {self.event.name} - Community Goal",
            description="Work together with all trainers to achieve this goal!",
            color=self.event.theme_color
        )
        
        # Get goal details
        goal_type = self.event.community_goal.get('type', 'Unknown')
        target = self.event.community_goal.get('target', 0)
        current = self.event.community_goal.get('current', 0)
        percentage = int((current / target) * 100) if target > 0 else 0
        description = self.event.community_goal.get('description', 'No description available')
        reward = self.event.community_goal.get('reward', 'No reward specified')
        
        # Add goal details
        embed.add_field(name="Goal", value=description, inline=False)
        embed.add_field(name="Progress", value=f"{current:,} / {target:,} ({percentage}%)", inline=True)
        embed.add_field(name="Reward", value=reward, inline=True)
        
        # Create progress bar
        progress_bar = ""
        filled = int(percentage / 10)
        empty = 10 - filled
        
        progress_bar = "▰" * filled + "▱" * empty
        
        embed.add_field(name="Progress Bar", value=progress_bar, inline=False)
        
        # Add user contribution if applicable
        user_contrib = await self.cog.get_user_event_contribution(self.user_id, self.event.id)
        if user_contrib > 0:
            user_percentage = round((user_contrib / current) * 100, 1) if current > 0 else 0
            embed.add_field(name="Your Contribution", value=f"{user_contrib:,} ({user_percentage}%)", inline=True)
        
        # Create view with back button
        view = discord.ui.View()
        
        @discord.ui.button(label="Back to Event", style=discord.ButtonStyle.secondary)
        async def back_to_event(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != self.user_id:
                await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                return
                
            # Show the main event view
            embed = self.event.create_embed(self.user_id)
            await i.response.edit_message(embed=embed, view=self)
                
        # Add back button
        view.add_item(back_to_event)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Set Reminder", style=discord.ButtonStyle.secondary, custom_id="set_reminder")
    async def set_reminder(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set a reminder for when the event starts."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
            return
            
        status = self.event.get_status()
        if status != EventStatus.UPCOMING:
            await interaction.response.send_message("This event has already started or ended.", ephemeral=True)
            return
            
        # Set reminder in database
        db = self.cog.db
        await db.execute(
            """
            INSERT INTO event_reminders (user_id, event_id, remind_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, event_id) DO UPDATE SET remind_at = ?
            """,
            (self.user_id, self.event.id, self.event.start_date.timestamp(), self.event.start_date.timestamp())
        )
        
        await interaction.response.send_message(
            f"You will be reminded when the **{self.event.name}** event starts!", 
            ephemeral=True
        )


class EventListView(NavigationView):
    """Interactive view for browsing events."""
    
    def __init__(self, user_id: str, events: List[Event], cog: 'EventCog'):
        super().__init__(user_id=user_id)
        self.events = events
        self.cog = cog
        
        # Initialize page tracking
        self.page_tracker = PageTracker(self.events, 3)  # 3 events per page
        
        # Add buttons for event interaction
        self.setup_buttons()
        
    def setup_buttons(self):
        """Setup navigation buttons and event selection."""
        self.clear_items()
        
        # Add navigation buttons
        self.add_navigation_buttons()
        
        # Add event selection buttons (up to 3 per page)
        current_page_items = self.page_tracker.get_current_page_items()
        for i, event in enumerate(current_page_items):
            # Determine event status
            status = event.get_status()
            status_text = status.name.replace('_', ' ').title()
            
            # Create a button for the event
            button = MenuButton(
                label=f"{i+1}. {event.name[:20]}...",
                emoji=event.icon,
                value=event.id,
                description=f"Status: {status_text}"
            )
            
            self.add_item(button)
            
    async def handle_select(self, interaction: discord.Interaction, value: str):
        """Handle selection of an event."""
        event_id = value
        event = event_manager.get_event(event_id)
        
        if not event:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return
            
        # Create event view and embed
        view = EventView(self.user_id, event, self.cog)
        embed = event.create_embed(self.user_id)
        
        await interaction.response.edit_message(embed=embed, view=view)
        
    async def on_page_change(self, interaction: discord.Interaction):
        """Handle page change."""
        self.setup_buttons()
        
        # Create page summary embed
        embed = self.create_list_embed()
        
        await interaction.response.edit_message(embed=embed, view=self)
        
    def create_list_embed(self) -> discord.Embed:
        """Create an embed showing the list of events."""
        embed = create_themed_embed(
            self.user_id,
            title=f"🎉 Seasonal Events",
            description="Select an event to view details and participate.",
            color=ThemeColorType.PRIMARY
        )
        
        # Add page information
        current_page = self.page_tracker.current_page + 1
        total_pages = self.page_tracker.total_pages
        embed.set_footer(text=f"Page {current_page}/{total_pages}")
        
        # Add event preview for current page
        events = self.page_tracker.get_current_page_items()
        
        for i, event in enumerate(events):
            # Get status info
            status = event.get_status()
            status_text = status.name.replace('_', ' ').title()
            
            time_text = ""
            if status == EventStatus.UPCOMING:
                time_until = event.time_until_start()
                days = time_until.days
                
                if days > 0:
                    time_text = f"Starts in {days} days"
                else:
                    hours = time_until.seconds // 3600
                    if hours > 0:
                        time_text = f"Starts in {hours} hours"
                    else:
                        minutes = (time_until.seconds // 60) % 60
                        time_text = f"Starts in {minutes} minutes"
            elif status == EventStatus.ACTIVE:
                time_until = event.time_until_end()
                days = time_until.days
                
                if days > 0:
                    time_text = f"Ends in {days} days"
                else:
                    hours = time_until.seconds // 3600
                    if hours > 0:
                        time_text = f"Ends in {hours} hours"
                    else:
                        minutes = (time_until.seconds // 60) % 60
                        time_text = f"Ends in {minutes} minutes"
                        
            # Create field for the event
            field_name = f"{i+1}. {event.icon} {event.name}"
            field_value = f"Status: **{status_text}**\n"
            
            if time_text:
                field_value += f"{time_text}\n"
                
            # Add special content summary
            specials = []
            if event.special_encounters:
                specials.append(f"{len(event.special_encounters)} special encounters")
            if event.special_items:
                specials.append(f"{len(event.special_items)} special items")
            if event.quests:
                specials.append(f"{len(event.quests)} event quests")
            if event.community_goal:
                specials.append("community goal")
                
            if specials:
                field_value += "Features: " + ", ".join(specials)
                
            embed.add_field(name=field_name, value=field_value, inline=False)
            
        return embed


class EventCog(commands.Cog):
    """
    Manages Seasonal Events and Limited-Time Content.
    
    Provides commands for viewing, participating in, and tracking seasonal
    events with special encounters, items, and quests.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        
        # Ensure event manager is initialized
        from src.models.event_manager import init_event_manager
        self.event_manager = init_event_manager(event_dir="data/events")
        
        # Start background tasks
        self.check_event_status.start()
        self.check_event_reminders.start()
        
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.check_event_status.cancel()
        self.check_event_reminders.cancel()
    
    async def show_event_quests(self, interaction: discord.Interaction, event_id: str):
        """Show quests for a specific event."""
        user_id = str(interaction.user.id)
        event = self.event_manager.get_event(event_id)
        
        if not event:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return
            
        if not event.quests:
            await interaction.response.send_message("This event has no special quests.", ephemeral=True)
            return
            
        # Get the quest manager
        from src.models.quest_manager import quest_manager
        if not quest_manager:
            await interaction.response.send_message("Quest system is not available.", ephemeral=True)
            return
            
        # Get user quest manager
        quest_cog = self.bot.get_cog("QuestCog")
        if not quest_cog:
            await interaction.response.send_message("Quest system is not available.", ephemeral=True)
            return
            
        user_manager = await quest_cog.get_user_quest_manager(user_id)
        
        # Get quests for this event
        event_quests = []
        for quest_id in event.quests:
            quest = quest_manager.get_quest(quest_id)
            if quest:
                event_quests.append(quest)
                
        if not event_quests:
            await interaction.response.send_message("No quests available for this event.", ephemeral=True)
            return
            
        # Import QuestListView here to avoid circular imports
        from src.cogs.quest_cog import QuestListView
        view = QuestListView(user_id, event_quests, user_manager, quest_cog)
        embed = view.create_list_embed()
        
        # Update embed title to reflect event quests
        embed.title = f"{event.icon} {event.name} - Event Quests"
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def purchase_event_item(self, interaction: discord.Interaction, event_id: str, item: Dict[str, Any]) -> tuple[bool, str]:
        """Purchase an event item."""
        user_id = str(interaction.user.id)
        
        # Get price and item details
        item_id = item.get('id', '')
        name = item.get('name', 'Event Item')
        price = item.get('price', 100)
        quantity = item.get('quantity', 1)
        
        # Check user's token balance
        result = await self.db.fetchone(
            "SELECT tokens FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        if not result:
            return False, "You don't have an account set up."
            
        token_balance = result['tokens']
        
        # Check if user can afford the item
        if token_balance < price:
            return False, f"You don't have enough tokens. Price: {price}, Your balance: {token_balance}"
            
        # Purchase the item
        # 1. Deduct tokens
        await self.db.execute(
            "UPDATE users SET tokens = tokens - ? WHERE user_id = ?",
            (price, user_id)
        )
        
        # 2. Add item to inventory
        await self.db.execute(
            """
            INSERT INTO items (user_id, item_id, quantity) 
            VALUES (?, ?, ?) 
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
            """,
            (user_id, item_id, quantity, quantity)
        )
        
        # 3. Track purchase in event purchases
        await self.db.execute(
            """
            INSERT INTO event_purchases (user_id, event_id, item_id, quantity, price, purchased_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, event_id, item_id, quantity, price, time.time())
        )
        
        return True, f"Successfully purchased {quantity}x {name} for {price} tokens!"
    
    async def get_user_event_contribution(self, user_id: str, event_id: str) -> int:
        """Get a user's contribution to a community goal."""
        result = await self.db.fetchone(
            """
            SELECT SUM(contribution) as total 
            FROM event_contributions 
            WHERE user_id = ? AND event_id = ?
            """,
            (user_id, event_id)
        )
        
        return result['total'] if result and result['total'] else 0
    
    async def add_user_event_contribution(self, user_id: str, event_id: str, amount: int, contribution_type: str) -> bool:
        """Add to a user's contribution for a community goal."""
        event = self.event_manager.get_event(event_id)
        if not event or not event.community_goal:
            return False
            
        # Add to user contribution
        await self.db.execute(
            """
            INSERT INTO event_contributions (user_id, event_id, contribution, contribution_type, contributed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, event_id, amount, contribution_type, time.time())
        )
        
        # Update event community goal
        self.event_manager.update_community_goal(event_id, amount)
        
        return True
    
    @tasks.loop(hours=1)
    async def check_event_status(self):
        """Periodically check for event status changes."""
        logger.info("Checking event status...")
        
        now = datetime.now()
        
        # Check for events that just started
        for event in self.event_manager.events.values():
            # Calculate time difference from start
            if event.start_date <= now and event.start_date > now - timedelta(hours=1):
                # Event just started in the last hour
                await self.announce_event_start(event)
                
            # Calculate time difference from end
            if event.end_date <= now and event.end_date > now - timedelta(hours=1):
                # Event just ended in the last hour
                await self.announce_event_end(event)
    
    @check_event_status.before_loop
    async def before_check_event_status(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
    
    @tasks.loop(minutes=15)
    async def check_event_reminders(self):
        """Check for event reminders that need to be sent."""
        logger.info("Checking event reminders...")
        
        now = time.time()
        
        # Get reminders that are due
        results = await self.db.fetchall(
            """
            SELECT user_id, event_id 
            FROM event_reminders 
            WHERE remind_at <= ? AND reminded = 0
            """,
            (now,)
        )
        
        if not results:
            return
            
        for result in results:
            user_id = result['user_id']
            event_id = result['event_id']
            
            # Get event
            event = self.event_manager.get_event(event_id)
            if not event:
                continue
                
            # Send DM reminder
            try:
                user = await self.bot.fetch_user(int(user_id))
                if not user:
                    continue
                    
                embed = create_themed_embed(
                    user_id,
                    title=f"{event.icon} Event Starting: {event.name}",
                    description=f"The event you were waiting for is starting now!\n\n{event.description}",
                    color=event.theme_color
                )
                
                # Add quick info
                features = []
                if event.special_encounters:
                    features.append(f"• {len(event.special_encounters)} special encounters")
                if event.special_items:
                    features.append(f"• {len(event.special_items)} special items")
                if event.quests:
                    features.append(f"• {len(event.quests)} event quests")
                if event.community_goal:
                    features.append(f"• Community goal with rewards")
                    
                if features:
                    embed.add_field(name="Event Features", value="\n".join(features), inline=False)
                    
                # Add end date
                end_date_str = event.end_date.strftime("%B %d, %Y")
                embed.set_footer(text=f"Event ends on {end_date_str}")
                
                # Add banner if available
                if event.banner_url:
                    embed.set_image(url=event.banner_url)
                    
                await user.send(embed=embed)
                
                # Mark as reminded
                await self.db.execute(
                    "UPDATE event_reminders SET reminded = 1 WHERE user_id = ? AND event_id = ?",
                    (user_id, event_id)
                )
                
            except Exception as e:
                logger.error(f"Error sending event reminder to user {user_id}: {e}")
                
    @check_event_reminders.before_loop
    async def before_check_event_reminders(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
    
    async def announce_event_start(self, event: Event):
        """Announce that an event has started."""
        # Get announcement channel from settings
        # This would be configured per server
        # For now, just log it
        logger.info(f"Event started: {event.name}")
        
        # In a real implementation, this would send announcements to configured channels
    
    async def announce_event_end(self, event: Event):
        """Announce that an event has ended."""
        # Get announcement channel from settings
        # This would be configured per server
        # For now, just log it
        logger.info(f"Event ended: {event.name}")
        
        # In a real implementation, this would send announcements to configured channels
    
    @app_commands.command(name="events", description="View current and upcoming events")
    async def events(self, interaction: discord.Interaction):
        """View current and upcoming events."""
        user_id = str(interaction.user.id)
        
        # Get active and upcoming events
        active_events = self.event_manager.get_active_events()
        upcoming_events = self.event_manager.get_upcoming_events()
        
        if not active_events and not upcoming_events:
            embed = create_themed_embed(
                user_id,
                title="🎉 Seasonal Events",
                description="There are no active or upcoming events at this time.",
                color=ThemeColorType.PRIMARY
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Create summary embed
        embed = create_themed_embed(
            user_id,
            title="🎉 Seasonal Events",
            description="Special limited-time events with unique content!",
            color=ThemeColorType.PRIMARY
        )
        
        # Add active events summary
        if active_events:
            active_text = ""
            for event in active_events[:3]:
                time_until = event.time_until_end()
                days = time_until.days
                
                if days > 0:
                    time_str = f"{days}d remaining"
                else:
                    hours = time_until.seconds // 3600
                    if hours > 0:
                        time_str = f"{hours}h remaining"
                    else:
                        minutes = (time_until.seconds // 60) % 60
                        time_str = f"{minutes}m remaining"
                        
                active_text += f"• {event.icon} **{event.name}** - {time_str}\n"
                
            if len(active_events) > 3:
                active_text += f"...and {len(active_events) - 3} more!"
                
            embed.add_field(
                name=f"Active Events ({len(active_events)})",
                value=active_text,
                inline=False
            )
            
        # Add upcoming events summary
        if upcoming_events:
            upcoming_text = ""
            for event in upcoming_events[:3]:
                time_until = event.time_until_start()
                days = time_until.days
                
                if days > 0:
                    time_str = f"in {days}d"
                else:
                    hours = time_until.seconds // 3600
                    if hours > 0:
                        time_str = f"in {hours}h"
                    else:
                        minutes = (time_until.seconds // 60) % 60
                        time_str = f"in {minutes}m"
                        
                upcoming_text += f"• {event.icon} **{event.name}** - Starts {time_str}\n"
                
            if len(upcoming_events) > 3:
                upcoming_text += f"...and {len(upcoming_events) - 3} more!"
                
            embed.add_field(
                name=f"Upcoming Events ({len(upcoming_events)})",
                value=upcoming_text,
                inline=False
            )
            
        # Create view with buttons to see different categories
        view = discord.ui.View()
        
        @discord.ui.button(label="Active Events", style=discord.ButtonStyle.success)
        async def view_active(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != user_id:
                await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                return
                
            if not active_events:
                await i.response.send_message("There are no active events.", ephemeral=True)
                return
                
            # Show active events
            view = EventListView(user_id, active_events, self)
            embed = view.create_list_embed()
            embed.title = "🎉 Active Events"
            
            await i.response.edit_message(embed=embed, view=view)
            
        @discord.ui.button(label="Upcoming Events", style=discord.ButtonStyle.primary)
        async def view_upcoming(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != user_id:
                await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                return
                
            if not upcoming_events:
                await i.response.send_message("There are no upcoming events.", ephemeral=True)
                return
                
            # Show upcoming events
            view = EventListView(user_id, upcoming_events, self)
            embed = view.create_list_embed()
            embed.title = "🎉 Upcoming Events"
            
            await i.response.edit_message(embed=embed, view=view)
            
        @discord.ui.button(label="Recent Events", style=discord.ButtonStyle.secondary)
        async def view_recent(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != user_id:
                await i.response.send_message("You cannot interact with someone else's event view.", ephemeral=True)
                return
                
            # Get recently ended events
            recent_events = self.event_manager.get_recently_ended_events()
            
            if not recent_events:
                await i.response.send_message("There are no recently ended events.", ephemeral=True)
                return
                
            # Show recent events
            view = EventListView(user_id, recent_events, self)
            embed = view.create_list_embed()
            embed.title = "🎉 Recently Ended Events"
            
            await i.response.edit_message(embed=embed, view=view)
            
        # Add buttons to view
        view.add_item(view_active)
        view.add_item(view_upcoming)
        view.add_item(view_recent)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="event_info", description="View details about a specific event")
    @app_commands.describe(event_id="The ID of the event to view")
    async def event_info(self, interaction: discord.Interaction, event_id: str):
        """View detailed information about a specific event."""
        user_id = str(interaction.user.id)
        
        # Get event
        event = self.event_manager.get_event(event_id)
        if not event:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return
            
        # Create event view and embed
        view = EventView(user_id, event, self)
        embed = event.create_embed(user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    # Event listeners to track contributions to community goals
    
    @commands.Cog.listener()
    async def on_veramon_caught(self, user_id: str, veramon_data: Dict[str, Any]):
        """Track catches for active event community goals."""
        # Check for active events with community goals
        active_events = self.event_manager.get_active_events()
        
        for event in active_events:
            if not event.community_goal:
                continue
                
            goal_type = event.community_goal.get('type')
            
            # If goal is to catch Veramon
            if goal_type in ['catch', 'catches', 'veramon_caught']:
                await self.add_user_event_contribution(user_id, event.id, 1, 'catch')
                
            # If goal is to catch specific Veramon
            elif goal_type == 'catch_specific':
                target = event.community_goal.get('target_veramon')
                if target and veramon_data.get('veramon_id') == target:
                    await self.add_user_event_contribution(user_id, event.id, 1, 'catch_specific')
    
    @commands.Cog.listener()
    async def on_battle_complete(self, user_id: str, battle_data: Dict[str, Any]):
        """Track battles for active event community goals."""
        is_winner = battle_data.get('is_winner', False)
        
        # Check for active events with community goals
        active_events = self.event_manager.get_active_events()
        
        for event in active_events:
            if not event.community_goal:
                continue
                
            goal_type = event.community_goal.get('type')
            
            # If goal is to complete battles
            if goal_type in ['battle', 'battles', 'battles_completed']:
                await self.add_user_event_contribution(user_id, event.id, 1, 'battle')
                
            # If goal is to win battles
            elif goal_type in ['win', 'wins', 'battles_won'] and is_winner:
                await self.add_user_event_contribution(user_id, event.id, 1, 'win')
    
    @commands.Cog.listener()
    async def on_exploration(self, user_id: str, exploration_data: Dict[str, Any]):
        """Track exploration for active event community goals."""
        # Check for active events with community goals
        active_events = self.event_manager.get_active_events()
        
        for event in active_events:
            if not event.community_goal:
                continue
                
            goal_type = event.community_goal.get('type')
            
            # If goal is to explore
            if goal_type in ['explore', 'exploration']:
                await self.add_user_event_contribution(user_id, event.id, 1, 'explore')

async def setup(bot):
    """Add the EventCog to the bot."""
    # Ensure database has required tables
    db = Database()
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS event_reminders (
            user_id TEXT,
            event_id TEXT,
            remind_at REAL,
            reminded INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, event_id)
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS event_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            event_id TEXT,
            item_id TEXT,
            quantity INTEGER,
            price INTEGER,
            purchased_at REAL
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS event_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            event_id TEXT,
            contribution INTEGER,
            contribution_type TEXT,
            contributed_at REAL
        )
    """)
    
    # Create data directories if they don't exist
    os.makedirs("data/events", exist_ok=True)
    
    # Add the cog
    await bot.add_cog(EventCog(bot))
