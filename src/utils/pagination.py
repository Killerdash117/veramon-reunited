import discord
from typing import List, Any, Callable, Optional, Dict, Union
from math import ceil

class PaginationView(discord.ui.View):
    """
    A reusable pagination view for Discord embeds.
    Can be used for any command that needs to display paginated data.
    """
    
    def __init__(
        self, 
        data: List[Any],
        page_size: int = 10,
        timeout: int = 180,
        title: str = "Results",
        empty_message: str = "No results found.",
        formatter: Callable[[Any], str] = str,
        author: Optional[discord.Member] = None,
        **kwargs
    ):
        """
        Initialize a new pagination view.
        
        Args:
            data: List of items to paginate
            page_size: Number of items per page
            timeout: View timeout in seconds
            title: Title for the embed
            empty_message: Message to display when data is empty
            formatter: Function to format each item in the data list
            author: The user who invoked the command
            **kwargs: Additional data to pass to the formatter
        """
        super().__init__(timeout=timeout)
        self.data = data
        self.page_size = page_size
        self.title = title
        self.empty_message = empty_message
        self.formatter = formatter
        self.author = author
        self.current_page = 1
        self.total_pages = max(1, ceil(len(data) / page_size))
        self.kwargs = kwargs
        
        # Disable navigation buttons if not needed
        self.update_buttons()
        
    def update_buttons(self):
        """Update button states based on current page."""
        # First page button
        self.first_page_button.disabled = self.current_page == 1
        
        # Previous page button
        self.prev_button.disabled = self.current_page == 1
        
        # Next page button
        self.next_button.disabled = self.current_page == self.total_pages
        
        # Last page button
        self.last_page_button.disabled = self.current_page == self.total_pages
        
    def get_current_page_data(self) -> List[Any]:
        """Get the data for the current page."""
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.data))
        return self.data[start_idx:end_idx]
        
    def create_embed(self) -> discord.Embed:
        """Create an embed for the current page."""
        embed = discord.Embed(title=self.title, color=discord.Color.blue())
        
        if not self.data:
            embed.description = self.empty_message
            return embed
            
        page_data = self.get_current_page_data()
        content = "\n".join(self.formatter(item, **self.kwargs) for item in page_data)
        embed.description = content
        
        # Add page number and total count
        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages} • {len(self.data)} total items")
        
        # Add author if provided
        if self.author:
            embed.set_author(name=self.author.display_name, icon_url=self.author.display_avatar.url)
            
        return embed
        
    async def refresh_view(self, interaction: discord.Interaction):
        """Refresh the view with updated data."""
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        
    @discord.ui.button(label="<<", style=discord.ButtonStyle.gray)
    async def first_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the first page."""
        if interaction.user != self.author and self.author is not None:
            await interaction.response.send_message("You can't use these controls.", ephemeral=True)
            return
            
        self.current_page = 1
        await self.refresh_view(interaction)
        
    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page."""
        if interaction.user != self.author and self.author is not None:
            await interaction.response.send_message("You can't use these controls.", ephemeral=True)
            return
            
        self.current_page = max(1, self.current_page - 1)
        await self.refresh_view(interaction)
        
    @discord.ui.button(label="🔄", style=discord.ButtonStyle.green)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the current page."""
        if interaction.user != self.author and self.author is not None:
            await interaction.response.send_message("You can't use these controls.", ephemeral=True)
            return
            
        await self.refresh_view(interaction)
        
    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page."""
        if interaction.user != self.author and self.author is not None:
            await interaction.response.send_message("You can't use these controls.", ephemeral=True)
            return
            
        self.current_page = min(self.total_pages, self.current_page + 1)
        await self.refresh_view(interaction)
        
    @discord.ui.button(label=">>", style=discord.ButtonStyle.gray)
    async def last_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the last page."""
        if interaction.user != self.author and self.author is not None:
            await interaction.response.send_message("You can't use these controls.", ephemeral=True)
            return
            
        self.current_page = self.total_pages
        await self.refresh_view(interaction)
        
    async def on_timeout(self):
        """Handle view timeout by disabling all buttons."""
        for item in self.children:
            item.disabled = True

# Example formatters for common data types
def format_veramon(veramon: Dict[str, Any], **kwargs) -> str:
    """Format a Veramon entry for display in paginated results."""
    name = veramon.get("nickname") or veramon.get("name", "Unknown")
    level = veramon.get("level", 1)
    capture_id = veramon.get("id", "?")
    shiny = "✨ " if veramon.get("shiny", False) else ""
    types = "/".join(veramon.get("type", ["Normal"]))
    
    return f"{shiny}**{name}** (Lvl {level}, ID: {capture_id}) - {types}"

def format_trade(trade: Dict[str, Any], **kwargs) -> str:
    """Format a trade entry for display in paginated results."""
    trade_id = trade.get("id", "?")
    status = trade.get("status", "unknown").capitalize()
    
    initiator = f"<@{trade['initiator_id']}>" if "initiator_id" in trade else "Unknown"
    recipient = f"<@{trade['recipient_id']}>" if "recipient_id" in trade else "Unknown"
    
    created_at = trade.get("created_at", "Unknown time")
    if isinstance(created_at, str) and len(created_at) > 10:
        created_at = created_at[:10]  # Truncate to just the date
        
    return f"**Trade #{trade_id}** - {status}\n{initiator} ⟷ {recipient} • {created_at}"

def format_battle(battle: Dict[str, Any], **kwargs) -> str:
    """Format a battle entry for display in paginated results."""
    battle_id = battle.get("id", "?")
    status = battle.get("status", "unknown").capitalize()
    battle_type = battle.get("battle_type", "unknown").upper()
    
    participants = battle.get("participants", [])
    participant_text = " vs ".join([f"<@{p}>" for p in participants[:2]])
    
    if battle.get("winner_id"):
        result = f"Winner: <@{battle['winner_id']}>"
    else:
        result = "No winner yet"
        
    return f"**Battle #{battle_id}** - {battle_type} - {status}\n{participant_text} • {result}"
