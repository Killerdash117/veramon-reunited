import discord
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, ForwardRef
QuestCog = ForwardRef('QuestCog')

from src.models.quest import Quest, QuestType, QuestStatus, QuestRequirementType, QuestRewardType, UserQuestManager
from src.models.quest_manager import quest_manager
from src.utils.ui_theme import theme_manager, ThemeColorType, create_themed_embed
from src.utils.interactive_components import NavigationView, MenuButton, PageTracker
from src.models.permissions import require_permission_level, PermissionLevel
from src.db.db import Database

logger = logging.getLogger('veramon.quest')

class QuestView(discord.ui.View):
    """Interactive view for quest details and management."""
    
    def __init__(self, user_id: str, quest: Quest, user_progress: Dict[str, Any], 
                cog: 'QuestCog', timeout: float = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.quest = quest
        self.user_progress = user_progress
        self.cog = cog
        
        # Add buttons based on quest status
        status = QuestStatus(user_progress.get('status', 0)) if user_progress else None
        
        if not status:
            # Quest not started
            self.add_item(discord.ui.Button(
                label="Accept Quest",
                style=discord.ButtonStyle.primary,
                custom_id="accept_quest"
            ))
        elif status == QuestStatus.IN_PROGRESS:
            # Quest in progress
            self.add_item(discord.ui.Button(
                label="View Progress",
                style=discord.ButtonStyle.secondary,
                custom_id="view_progress"
            ))
            self.add_item(discord.ui.Button(
                label="Abandon Quest",
                style=discord.ButtonStyle.danger,
                custom_id="abandon_quest"
            ))
        elif status == QuestStatus.COMPLETED:
            # Quest completed but rewards not claimed
            self.add_item(discord.ui.Button(
                label="Claim Rewards",
                style=discord.ButtonStyle.success,
                custom_id="claim_rewards"
            ))
        elif status == QuestStatus.CLAIMED:
            # Quest completed and rewards claimed
            if self.quest.repeatable:
                self.add_item(discord.ui.Button(
                    label="Repeat Quest",
                    style=discord.ButtonStyle.primary,
                    custom_id="repeat_quest"
                ))
        
    @discord.ui.button(label="Accept Quest", style=discord.ButtonStyle.primary, custom_id="accept_quest")
    async def accept_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accept the quest."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's quest.", ephemeral=True)
            return
            
        # Try to activate the quest
        user_manager = await self.cog.get_user_quest_manager(self.user_id)
        success = user_manager.activate_quest(self.quest)
        
        if success:
            # Quest activated successfully
            await self.cog.save_user_quest_manager(self.user_id, user_manager)
            
            # Update progress
            self.user_progress = user_manager.get_quest_progress(self.quest.id)
            
            # Create a new embed
            embed = self.quest.create_embed(self.user_progress)
            embed.title = f"📋 Quest Accepted: {self.quest.title}"
            
            # Add narrative if available
            if self.quest.narrative:
                embed.add_field(name="📜 Story", value=self.quest.narrative, inline=False)
                
            # Update buttons
            self.clear_items()
            self.add_item(discord.ui.Button(
                label="View Progress",
                style=discord.ButtonStyle.secondary,
                custom_id="view_progress"
            ))
            self.add_item(discord.ui.Button(
                label="Abandon Quest",
                style=discord.ButtonStyle.danger,
                custom_id="abandon_quest"
            ))
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Failed to activate quest
            await interaction.response.send_message(
                "Could not accept this quest. It may be on cooldown or prerequisites are not met.", 
                ephemeral=True
            )
    
    @discord.ui.button(label="View Progress", style=discord.ButtonStyle.secondary, custom_id="view_progress")
    async def view_progress(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View progress for the quest."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's quest.", ephemeral=True)
            return
            
        # Get updated progress
        user_manager = await self.cog.get_user_quest_manager(self.user_id)
        self.user_progress = user_manager.get_quest_progress(self.quest.id)
        
        # Create progress embed
        embed = self.quest.create_embed(self.user_progress)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Abandon Quest", style=discord.ButtonStyle.danger, custom_id="abandon_quest")
    async def abandon_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abandon the quest."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's quest.", ephemeral=True)
            return
            
        # Create confirmation view
        confirm_view = discord.ui.View(timeout=60)
        
        @discord.ui.button(label="Yes, Abandon", style=discord.ButtonStyle.danger)
        async def confirm_abandon(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != self.user_id:
                await i.response.send_message("You cannot interact with someone else's quest.", ephemeral=True)
                return
                
            # Remove the quest
            user_manager = await self.cog.get_user_quest_manager(self.user_id)
            active_quests = user_manager.get_active_quests()
            
            if self.quest.id in active_quests:
                del active_quests[self.quest.id]
                await self.cog.save_user_quest_manager(self.user_id, user_manager)
                
                embed = create_themed_embed(
                    self.user_id,
                    title="Quest Abandoned",
                    description=f"You have abandoned the quest **{self.quest.title}**.",
                    color_type=ThemeColorType.DANGER
                )
                
                await i.response.edit_message(embed=embed, view=None)
            else:
                await i.response.send_message("This quest is no longer active.", ephemeral=True)
        
        @discord.ui.button(label="No, Keep Quest", style=discord.ButtonStyle.secondary)
        async def cancel_abandon(i: discord.Interaction, b: discord.ui.Button):
            if str(i.user.id) != self.user_id:
                await i.response.send_message("You cannot interact with someone else's quest.", ephemeral=True)
                return
                
            # Just close the confirm dialog and go back to the quest view
            await i.response.edit_message(view=self)
        
        # Add the buttons to the confirmation view
        confirm_view.add_item(confirm_abandon)
        confirm_view.add_item(cancel_abandon)
        
        # Show confirmation dialog
        embed = create_themed_embed(
            self.user_id,
            title="Abandon Quest?",
            description=f"Are you sure you want to abandon the quest **{self.quest.title}**?\n\nAll progress will be lost.",
            color_type=ThemeColorType.WARNING
        )
        
        await interaction.response.edit_message(embed=embed, view=confirm_view)
    
    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.success, custom_id="claim_rewards")
    async def claim_rewards(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim rewards for the completed quest."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's quest.", ephemeral=True)
            return
            
        # Claim rewards
        user_manager = await self.cog.get_user_quest_manager(self.user_id)
        success = user_manager.claim_quest_rewards(self.quest)
        
        if success:
            # Rewards claimed successfully
            await self.cog.save_user_quest_manager(self.user_id, user_manager)
            
            # Process actual rewards
            await self.cog.process_quest_rewards(interaction, self.quest)
            
            # Update progress
            self.user_progress = user_manager.get_quest_progress(self.quest.id)
            
            # Create a new embed
            embed = create_themed_embed(
                self.user_id,
                title="🎁 Rewards Claimed!",
                description=f"You have claimed the rewards for **{self.quest.title}**.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # List rewards
            rewards_text = ""
            for reward in self.quest.rewards:
                reward_type = QuestRewardType[reward.get('type')].name
                amount = reward.get('amount', 1)
                item = reward.get('item', '')
                if item:
                    rewards_text += f"• {amount}x {reward.get('description', f'{item}')}\n"
                else:
                    rewards_text += f"• {amount}x {reward.get('description', reward_type)}\n"
                    
            embed.add_field(name="Rewards", value=rewards_text, inline=False)
            
            # Update buttons
            self.clear_items()
            if self.quest.repeatable:
                self.add_item(discord.ui.Button(
                    label="Repeat Quest",
                    style=discord.ButtonStyle.primary,
                    custom_id="repeat_quest"
                ))
                
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Failed to claim rewards
            await interaction.response.send_message(
                "Could not claim rewards for this quest. It may not be completed yet.", 
                ephemeral=True
            )
    
    @discord.ui.button(label="Repeat Quest", style=discord.ButtonStyle.primary, custom_id="repeat_quest")
    async def repeat_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Repeat the quest if it's repeatable."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot interact with someone else's quest.", ephemeral=True)
            return
            
        # Check if quest can be repeated
        user_manager = await self.cog.get_user_quest_manager(self.user_id)
        
        if user_manager.is_quest_on_cooldown(self.quest.id):
            # Quest is on cooldown
            cooldown_expiry = user_manager.get_cooldown_expiry(self.quest.id)
            now = time.time()
            remaining = cooldown_expiry - now
            
            if remaining > 0:
                hours, remainder = divmod(int(remaining), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                if hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m {seconds}s"
                    
                await interaction.response.send_message(
                    f"This quest is on cooldown. Available again in: {time_str}", 
                    ephemeral=True
                )
                return
        
        # Try to activate the quest again
        success = user_manager.activate_quest(self.quest)
        
        if success:
            # Quest activated successfully
            await self.cog.save_user_quest_manager(self.user_id, user_manager)
            
            # Update progress
            self.user_progress = user_manager.get_quest_progress(self.quest.id)
            
            # Create a new embed
            embed = self.quest.create_embed(self.user_progress)
            embed.title = f"📋 Quest Accepted Again: {self.quest.title}"
            
            # Update buttons
            self.clear_items()
            self.add_item(discord.ui.Button(
                label="View Progress",
                style=discord.ButtonStyle.secondary,
                custom_id="view_progress"
            ))
            self.add_item(discord.ui.Button(
                label="Abandon Quest",
                style=discord.ButtonStyle.danger,
                custom_id="abandon_quest"
            ))
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Failed to activate quest
            await interaction.response.send_message(
                "Could not repeat this quest. It may have reached its maximum completions.", 
                ephemeral=True
            )


class QuestListView(NavigationView):
    """Interactive view for browsing quests."""
    
    def __init__(self, user_id: str, quests: List[Quest], user_manager: UserQuestManager, 
                cog: 'QuestCog', quest_type: QuestType = None):
        super().__init__(user_id=user_id)
        self.quests = quests
        self.user_manager = user_manager
        self.cog = cog
        self.quest_type = quest_type
        
        # Initialize page tracking
        self.page_tracker = PageTracker(self.quests, 5)  # 5 quests per page
        
        # Add buttons for quest interaction
        self.setup_buttons()
        
    def setup_buttons(self):
        """Setup navigation buttons and quest selection."""
        self.clear_items()
        
        # Add navigation buttons
        self.add_navigation_buttons()
        
        # Add quest selection buttons (up to 5 per page)
        current_page_items = self.page_tracker.get_current_page_items()
        for i, quest in enumerate(current_page_items):
            # Determine quest status
            progress = self.user_manager.get_quest_progress(quest.id)
            status_text = "Not Started"
            
            if progress:
                status = QuestStatus(progress.get('status', 0))
                status_text = status.name.replace('_', ' ').title()
                
            # Create a button for the quest
            button = MenuButton(
                label=f"{i+1}. {quest.title[:20]}...",
                emoji=quest.icon,
                value=quest.id,
                description=f"Status: {status_text}"
            )
            
            self.add_item(button)
            
    async def handle_select(self, interaction: discord.Interaction, value: str):
        """Handle selection of a quest."""
        quest_id = value
        quest = quest_manager.get_quest(quest_id)
        
        if not quest:
            await interaction.response.send_message("Quest not found.", ephemeral=True)
            return
            
        # Get user progress for this quest
        progress = self.user_manager.get_quest_progress(quest.id)
        
        # Create quest view and embed
        view = QuestView(self.user_id, quest, progress, self.cog)
        embed = quest.create_embed(progress)
        
        await interaction.response.edit_message(embed=embed, view=view)
        
    async def on_page_change(self, interaction: discord.Interaction):
        """Handle page change."""
        self.setup_buttons()
        
        # Create page summary embed
        embed = self.create_list_embed()
        
        await interaction.response.edit_message(embed=embed, view=self)
        
    def create_list_embed(self) -> discord.Embed:
        """Create an embed showing the list of quests."""
        # Determine title based on quest type
        if self.quest_type:
            type_names = {
                QuestType.DAILY: "Daily Quests",
                QuestType.WEEKLY: "Weekly Quests",
                QuestType.STORY: "Story Quests",
                QuestType.ACHIEVEMENT: "Achievements",
                QuestType.EVENT: "Event Quests"
            }
            title = type_names.get(self.quest_type, "Quests")
        else:
            title = "Available Quests"
            
        embed = create_themed_embed(
            self.user_id,
            title=f"📋 {title}",
            description="Select a quest to view details and manage it.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add page information
        current_page = self.page_tracker.current_page + 1
        total_pages = self.page_tracker.total_pages
        embed.set_footer(text=f"Page {current_page}/{total_pages}")
        
        # Add quest preview for current page
        quests = self.page_tracker.get_current_page_items()
        
        for i, quest in enumerate(quests):
            # Get progress info
            progress = self.user_manager.get_quest_progress(quest.id)
            status_text = "Not Started"
            
            if progress:
                status = QuestStatus(progress.get('status', 0))
                status_text = status.name.replace('_', ' ').title()
                
                # Add progress percentage for in-progress quests
                if status == QuestStatus.IN_PROGRESS and 'requirements_progress' in progress:
                    total_reqs = len(quest.requirements)
                    completed_reqs = sum(1 for i, req in enumerate(quest.requirements) 
                                        if quest.check_requirement_progress(i, progress))
                                        
                    if total_reqs > 0:
                        percentage = int((completed_reqs / total_reqs) * 100)
                        status_text += f" ({percentage}%)"
            
            # Create field for the quest
            field_name = f"{i+1}. {quest.icon} {quest.title}"
            field_value = f"Status: **{status_text}**\n"
            
            # Add expiry info if applicable
            if quest.expiry:
                now = datetime.now()
                if quest.expiry > now:
                    time_left = quest.expiry - now
                    days = time_left.days
                    
                    if days > 0:
                        time_str = f"{days} days"
                    else:
                        hours = time_left.seconds // 3600
                        if hours > 0:
                            time_str = f"{hours} hours"
                        else:
                            minutes = (time_left.seconds // 60) % 60
                            time_str = f"{minutes} minutes"
                            
                    field_value += f"Expires in: **{time_str}**\n"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
            
        return embed

QuestCog = 'QuestCog'
