"""
Database administration commands for Veramon Reunited bot.

This module provides Discord commands for server administrators to manage
the SQLite database, including backup, restore, table management, and diagnostics.
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
import asyncio
import io
from datetime import datetime

from src.db.db_manager import get_db_manager
from src.core.security_integration import get_security_integration
from src.core.config_manager import get_config_value

class DatabaseAdminCog(commands.Cog):
    """Admin commands for database management."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_manager = get_db_manager()
        self.security = get_security_integration()
    
    @app_commands.command(name="db_backup", description="Create a backup of the database")
    @app_commands.default_permissions(administrator=True)
    async def db_backup(self, interaction: discord.Interaction, backup_name: Optional[str] = None):
        """Create a backup of the current database."""
        # Validate admin permissions (admin access only)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_backup", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Create a timestamp-based name if none provided
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        # Create the backup
        backup_path = self.db_manager.create_backup(backup_name)
        
        # Check if file is small enough to upload (Discord limit is 8MB for normal, 50MB for Nitro)
        file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        
        embed = discord.Embed(
            title="Database Backup",
            description=f"✅ Backup created: `{os.path.basename(backup_path)}`\n\nSize: {file_size_mb:.2f} MB",
            color=discord.Color.green()
        )
        
        # If file is small enough, attach it
        if file_size_mb < 8:  # Safe size for non-Nitro users
            backup_file = discord.File(backup_path, filename=os.path.basename(backup_path))
            await interaction.followup.send(embed=embed, file=backup_file, ephemeral=True)
        else:
            embed.add_field(
                name="Note", 
                value="The backup file is too large to attach directly. Access it on the server filesystem.",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="db_list_backups", description="List available database backups")
    @app_commands.default_permissions(administrator=True)
    async def db_list_backups(self, interaction: discord.Interaction):
        """List all available database backups."""
        # Validate admin permissions (admin access only)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_list_backups", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get list of backups
        backups = self.db_manager.list_backups()
        
        if not backups:
            await interaction.followup.send("❌ No database backups found.", ephemeral=True)
            return
        
        # Create paginated embeds if there are many backups
        embeds = []
        current_embed = discord.Embed(
            title="Database Backups",
            description="Available database backups:",
            color=discord.Color.blue()
        )
        
        for i, backup in enumerate(backups):
            # Add to current embed
            current_embed.add_field(
                name=f"{i+1}. {backup['filename']}",
                value=f"Created: {backup['created']}\nSize: {backup['size_mb']} MB",
                inline=False
            )
            
            # Create a new embed every 5 backups
            if (i + 1) % 5 == 0 and i < len(backups) - 1:
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="Database Backups (Continued)",
                    color=discord.Color.blue()
                )
        
        # Add the last embed if it has fields
        if len(current_embed.fields) > 0:
            embeds.append(current_embed)
        
        # Send the first embed
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            # Implement pagination for multiple embeds
            current_page = 0
            
            # Add page numbers
            for i, embed in enumerate(embeds):
                embed.set_footer(text=f"Page {i+1}/{len(embeds)}")
            
            message = await interaction.followup.send(embed=embeds[0], ephemeral=True)
            
            # If there are multiple pages, add navigation buttons
            # This would be implemented with Discord UI components
            # Since this is a complex implementation, consider using a separate pagination utility
    
    @app_commands.command(name="db_restore", description="Restore database from a backup")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(backup_name="Name of the backup file to restore")
    async def db_restore(self, interaction: discord.Interaction, backup_name: str):
        """Restore the database from a backup file."""
        # Validate permissions (dev access only for restore)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_restore", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Verify backup exists
        backups = self.db_manager.list_backups()
        backup_exists = False
        backup_path = ""
        
        for backup in backups:
            if backup["filename"] == backup_name:
                backup_exists = True
                backup_path = backup["path"]
                break
        
        if not backup_exists:
            await interaction.followup.send(f"❌ Backup '{backup_name}' not found.", ephemeral=True)
            return
        
        # Ask for confirmation before proceeding
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Database Restore",
            description=f"You are about to restore the database from backup: `{backup_name}`\n\n"
                       f"**WARNING**: This will replace ALL current data with the data from this backup. "
                       f"This action cannot be undone!\n\n"
                       f"Do you want to continue?",
            color=discord.Color.red()
        )
        
        # Using confirm button
        class ConfirmButtons(discord.ui.View):
            def __init__(self, timeout=60):
                super().__init__(timeout=timeout)
                self.value = None
            
            @discord.ui.button(label="Confirm Restore", style=discord.ButtonStyle.danger)
            async def confirm(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                await b_interaction.response.defer()
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                await b_interaction.response.defer()
                self.stop()
        
        view = ConfirmButtons()
        await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)
        
        # Wait for the user's confirmation
        await view.wait()
        
        if view.value is None:
            await interaction.followup.send("❌ Restore cancelled: Timed out", ephemeral=True)
            return
        elif view.value is False:
            await interaction.followup.send("✅ Restore cancelled", ephemeral=True)
            return
        
        # Proceed with restore
        # This is a highly critical operation that requires a full confirmation string
        success = self.db_manager.restore_backup(backup_path, confirm_text="CONFIRM_RESTORE")
        
        if success:
            await interaction.followup.send("✅ Database successfully restored from backup!", ephemeral=True)
            
            # Reload any necessary systems
            # This would depend on your bot's architecture
            await self.bot.get_cog("SystemCog").reload_systems()
        else:
            await interaction.followup.send("❌ Failed to restore database from backup.", ephemeral=True)
    
    @app_commands.command(name="db_table_info", description="Get information about database tables")
    @app_commands.default_permissions(administrator=True)
    async def db_table_info(self, interaction: discord.Interaction):
        """Get detailed information about database tables."""
        # Validate admin permissions (admin access only)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_table_info", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get table information
        table_info = self.db_manager.get_table_sizes()
        
        if not table_info:
            await interaction.followup.send("❌ No tables found in database.", ephemeral=True)
            return
        
        # Create paginated embeds
        embeds = []
        current_embed = discord.Embed(
            title="Database Tables",
            description="Size and structure information for all tables:",
            color=discord.Color.blue()
        )
        
        for i, table in enumerate(table_info):
            # Add to current embed
            value = (
                f"Rows: {table['rows']}\n"
                f"Size: {table['estimated_size_kb']} KB\n"
                f"Columns: {len(table['column_names'])}"
            )
            
            current_embed.add_field(
                name=f"{i+1}. {table['name']}",
                value=value,
                inline=True
            )
            
            # Create a new embed every 6 tables (2 rows of 3)
            if (i + 1) % 6 == 0 and i < len(table_info) - 1:
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="Database Tables (Continued)",
                    color=discord.Color.blue()
                )
        
        # Add the last embed if it has fields
        if len(current_embed.fields) > 0:
            embeds.append(current_embed)
        
        # Send the embeds
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            # Implement pagination for multiple embeds
            # Similar to the previous command
            for i, embed in enumerate(embeds):
                embed.set_footer(text=f"Page {i+1}/{len(embeds)}")
            
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
    
    @app_commands.command(name="db_clear_table", description="Clear all data from a specific table")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(table_name="Name of the table to clear")
    async def db_clear_table(self, interaction: discord.Interaction, table_name: str):
        """Clear all data from a specific database table."""
        # Validate dev permissions (dev access only for clear_table)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_clear_table", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if table exists
        table_info = self.db_manager.get_table_sizes()
        table_exists = any(table["name"] == table_name for table in table_info)
        
        if not table_exists:
            await interaction.followup.send(f"❌ Table '{table_name}' does not exist.", ephemeral=True)
            return
        
        # Find the table size for the warning message
        table_data = next((table for table in table_info if table["name"] == table_name), None)
        rows = table_data["rows"] if table_data else "unknown"
        
        # Ask for confirmation before proceeding
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Table Clear",
            description=f"You are about to clear ALL DATA from table: `{table_name}`\n\n"
                      f"This table contains approximately {rows} rows.\n\n"
                      f"**WARNING**: This will delete ALL data in this table. "
                      f"This action cannot be undone!\n\n"
                      f"Type the table name to confirm:",
            color=discord.Color.red()
        )
        
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
        # Wait for confirmation message with the exact table name
        def check(m):
            return m.author.id == interaction.user.id and m.content == table_name and \
                   m.channel.id == interaction.channel_id
        
        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Table clear cancelled: Confirmation timed out", ephemeral=True)
            return
        
        # Proceed with table clear
        success = self.db_manager.clear_table(table_name, confirm=True)
        
        if success:
            await interaction.followup.send(f"✅ Successfully cleared all data from table: `{table_name}`", 
                                          ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Failed to clear table: `{table_name}`", ephemeral=True)
    
    @app_commands.command(name="db_optimize", description="Optimize the database (run VACUUM)")
    @app_commands.default_permissions(administrator=True)
    async def db_optimize(self, interaction: discord.Interaction):
        """Optimize the database structure and reclaim space."""
        # Validate admin permissions (admin access only)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_optimize", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Confirm before proceeding
        confirm_embed = discord.Embed(
            title="Database Optimization",
            description="You are about to optimize the database structure (VACUUM operation).\n\n"
                       "This process can take some time for large databases and will temporarily "
                       "lock the database from other operations.\n\n"
                       "Do you want to continue?",
            color=discord.Color.gold()
        )
        
        # Using confirm button
        class ConfirmButtons(discord.ui.View):
            def __init__(self, timeout=60):
                super().__init__(timeout=timeout)
                self.value = None
            
            @discord.ui.button(label="Optimize Database", style=discord.ButtonStyle.primary)
            async def confirm(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                await b_interaction.response.defer()
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                await b_interaction.response.defer()
                self.stop()
        
        view = ConfirmButtons()
        await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)
        
        # Wait for the user's confirmation
        await view.wait()
        
        if view.value is None:
            await interaction.followup.send("❌ Database optimization cancelled: Timed out", ephemeral=True)
            return
        elif view.value is False:
            await interaction.followup.send("✅ Database optimization cancelled", ephemeral=True)
            return
        
        # Execute the vacuum
        # This might take time, so we'll update the message periodically
        progress_message = await interaction.followup.send("🔄 Optimizing database... This may take a moment.", 
                                                        ephemeral=True)
        
        # Run the operation (might be slow for large DBs)
        success = self.db_manager.vacuum_database()
        
        if success:
            await progress_message.edit(content="✅ Database optimization complete! Database file size has been optimized.")
        else:
            await progress_message.edit(content="❌ Database optimization failed.")

    @app_commands.command(name="db_reset", description="DANGEROUS: Reset the entire database")
    @app_commands.default_permissions(administrator=True)
    async def db_reset(self, interaction: discord.Interaction):
        """Reset the entire database, clearing all data."""
        # Validate dev permissions with highest security (dev access only)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_reset", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Create a confirmation embed with severe warning
        confirm_embed = discord.Embed(
            title="⚠️ CRITICAL WARNING: DATABASE RESET ⚠️",
            description="**YOU ARE ABOUT TO RESET THE ENTIRE DATABASE!**\n\n"
                        "This will:\n"
                        "- **DELETE ALL USER DATA**\n"
                        "- **DELETE ALL VERAMON CAPTURES**\n"
                        "- **DELETE ALL PROGRESS AND SETTINGS**\n"
                        "- **RESET THE DATABASE TO DEFAULTS**\n\n"
                        "**THIS ACTION CANNOT BE UNDONE!**\n\n"
                        "A backup will be created before reset, but all current data will be lost.\n\n"
                        "To confirm, you must type the following in the channel:\n"
                        "```\nI CONFIRM DATABASE RESET - ALL DATA WILL BE PERMANENTLY LOST\n```",
            color=discord.Color.dark_red()
        )
        
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
        # Wait for the exact confirmation message
        confirmation_text = "I CONFIRM DATABASE RESET - ALL DATA WILL BE PERMANENTLY LOST"
        
        def check(m):
            return m.author.id == interaction.user.id and m.content == confirmation_text and \
                   m.channel.id == interaction.channel_id
        
        try:
            await self.bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("✅ Database reset cancelled: Confirmation timed out", ephemeral=True)
            return
        
        # Second confirmation with button (double confirmation for dangerous operation)
        final_confirm_embed = discord.Embed(
            title="⚠️ FINAL CONFIRMATION: DATABASE RESET ⚠️",
            description="This is your final chance to cancel this operation.\n\n"
                        "Press the red button below to confirm database reset.",
            color=discord.Color.dark_red()
        )
        
        # Using confirm button
        class FinalConfirmButtons(discord.ui.View):
            def __init__(self, timeout=60):
                super().__init__(timeout=timeout)
                self.value = None
            
            @discord.ui.button(label="CONFIRM RESET DATABASE", style=discord.ButtonStyle.danger)
            async def confirm(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                await b_interaction.response.defer()
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                await b_interaction.response.defer()
                self.stop()
        
        view = FinalConfirmButtons()
        final_message = await interaction.followup.send(embed=final_confirm_embed, view=view, ephemeral=True)
        
        # Wait for the user's confirmation
        await view.wait()
        
        if view.value is None or view.value is False:
            await interaction.followup.send("✅ Database reset cancelled", ephemeral=True)
            return
        
        # Execute the reset
        await interaction.followup.send("🔄 Creating backup before reset...", ephemeral=True)
        
        # Reset the database with the confirmation
        success = self.db_manager.reset_database(confirm_text="CONFIRM_RESET")
        
        if success:
            # Notify about success
            success_embed = discord.Embed(
                title="Database Reset Complete",
                description="✅ The database has been successfully reset to defaults.\n\n"
                            "A backup of the previous data was created before resetting.\n\n"
                            "The bot will now restart to apply changes.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
            # Send a system-wide announcement
            system_channel_id = get_config_value("system_channel_id", None)
            if system_channel_id:
                try:
                    channel = self.bot.get_channel(int(system_channel_id))
                    if channel:
                        await channel.send("**SYSTEM NOTICE**: The database has been reset by an administrator. All user data has been cleared.")
                except Exception as e:
                    print(f"Failed to send system message: {e}")
            
            # Restart the bot to ensure clean state
            await asyncio.sleep(5)
            # Implement bot restart logic here
    
    @app_commands.command(name="db_analyze", description="Analyze database usage and get optimization recommendations")
    @app_commands.default_permissions(administrator=True)
    async def db_analyze(self, interaction: discord.Interaction):
        """Analyze database usage and get optimization recommendations."""
        # Validate admin permissions (admin access - safer operation)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_analyze", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Run the analysis
        analysis = self.db_manager.analyze_database_usage()
        
        if "error" in analysis:
            await interaction.followup.send(f"❌ Error analyzing database: {analysis['error']}", ephemeral=True)
            return
        
        # Create main embed with overview
        main_embed = discord.Embed(
            title="Database Analysis",
            description=f"Total Size: **{analysis['total_size_mb']:.2f} MB**\n"
                       f"Tables: **{len(analysis['tables'])}**\n"
                       f"Indices: **{len(analysis['indices'])}**",
            color=discord.Color.blue()
        )
        
        # Add recommendations
        if analysis["recommendations"]:
            recommendations = ""
            for i, rec in enumerate(analysis["recommendations"], 1):
                impact_emoji = "🔴" if rec["impact"] == "high" else "🟠" if rec["impact"] == "medium" else "🟡"
                recommendations += f"{i}. {impact_emoji} {rec['description']}\n"
            
            main_embed.add_field(
                name="Recommendations",
                value=recommendations,
                inline=False
            )
        else:
            main_embed.add_field(
                name="Recommendations",
                value="✅ No optimization recommendations - database appears healthy!",
                inline=False
            )
        
        # Sort tables by size (largest first)
        tables = sorted(analysis["tables"], key=lambda x: x["estimated_size_kb"], reverse=True)
        
        # Add top 5 largest tables
        top_tables = tables[:5]
        table_info = ""
        for table in top_tables:
            table_info += f"**{table['name']}**: {table['rows']} rows, {table['estimated_size_kb']:.2f} KB\n"
        
        main_embed.add_field(
            name="Largest Tables",
            value=table_info if table_info else "No tables found",
            inline=False
        )
        
        # Add footer with timestamp
        main_embed.set_footer(text=f"Analysis performed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create action buttons
        class AnalysisActions(discord.ui.View):
            def __init__(self, cog, timeout=60):
                super().__init__(timeout=timeout)
                self.cog = cog
            
            @discord.ui.button(label="View All Tables", style=discord.ButtonStyle.secondary)
            async def view_tables(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                # Create paginated embeds for tables
                tables_embeds = []
                current_embed = discord.Embed(
                    title="Database Tables",
                    color=discord.Color.blue()
                )
                
                for i, table in enumerate(tables):
                    value = (
                        f"**Rows**: {table['rows']}\n"
                        f"**Size**: {table['estimated_size_kb']:.2f} KB\n"
                        f"**Columns**: {table['columns']}\n"
                        f"**Indices**: {table['indices']}"
                    )
                    
                    current_embed.add_field(
                        name=f"{table['name']}",
                        value=value,
                        inline=True
                    )
                    
                    # Create a new embed every 9 tables (3 rows of 3)
                    if (i + 1) % 9 == 0 and i < len(tables) - 1:
                        tables_embeds.append(current_embed)
                        current_embed = discord.Embed(
                            title="Database Tables (Continued)",
                            color=discord.Color.blue()
                        )
                
                # Add the last embed if it has fields
                if len(current_embed.fields) > 0:
                    tables_embeds.append(current_embed)
                
                # Add page numbers
                for i, embed in enumerate(tables_embeds):
                    embed.set_footer(text=f"Page {i+1}/{len(tables_embeds)}")
                
                await b_interaction.response.send_message(embed=tables_embeds[0], ephemeral=True)
            
            @discord.ui.button(label="Optimize Database", style=discord.ButtonStyle.primary)
            async def optimize_db(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                # Execute optimization
                await b_interaction.response.defer(ephemeral=True)
                
                # First clear temporary data
                await b_interaction.followup.send("🔄 Cleaning temporary data...", ephemeral=True)
                self.cog.db_manager.clean_temporary_data()
                
                # Then vacuum the database
                await b_interaction.followup.send("🔄 Optimizing database structure (VACUUM)...", ephemeral=True)
                success = self.cog.db_manager.vacuum_database()
                
                if success:
                    await b_interaction.followup.send("✅ Database optimization complete!", ephemeral=True)
                else:
                    await b_interaction.followup.send("❌ Database optimization failed.", ephemeral=True)
        
        # Send the embed with action buttons
        view = AnalysisActions(self)
        await interaction.followup.send(embed=main_embed, view=view, ephemeral=True)
    
    @app_commands.command(name="db_clean_temp", description="Clean temporary data from the database")
    @app_commands.default_permissions(administrator=True)
    async def db_clean_temp(self, interaction: discord.Interaction):
        """Clean temporary and old data from the database."""
        # Validate admin permissions (admin access only)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_clean_temp", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get retention settings from config
        config = self.db_manager.config
        retention_days = config.get("temp_data_retention_days", 7)
        
        # Confirm operation
        confirm_embed = discord.Embed(
            title="Database Cleanup",
            description=f"You are about to clean up temporary data older than {retention_days} days.\n\n"
                       f"This includes:\n"
                       f"- Expired spawn data\n"
                       f"- Completed battle records\n"
                       f"- Completed trades\n"
                       f"- Old event reminders\n\n"
                       f"This action cannot be undone, but only affects temporary/historical data.",
            color=discord.Color.gold()
        )
        
        # Using confirm button
        class ConfirmButtons(discord.ui.View):
            def __init__(self, timeout=60):
                super().__init__(timeout=timeout)
                self.value = None
            
            @discord.ui.button(label="Clean Temporary Data", style=discord.ButtonStyle.primary)
            async def confirm(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                await b_interaction.response.defer()
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                await b_interaction.response.defer()
                self.stop()
        
        view = ConfirmButtons()
        await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)
        
        # Wait for the user's confirmation
        await view.wait()
        
        if view.value is None:
            await interaction.followup.send("❌ Cleanup cancelled: Timed out", ephemeral=True)
            return
        elif view.value is False:
            await interaction.followup.send("✅ Cleanup cancelled", ephemeral=True)
            return
        
        # Execute the cleanup
        progress_message = await interaction.followup.send("🔄 Cleaning temporary data...", ephemeral=True)
        
        success = self.db_manager.clean_temporary_data()
        
        if success:
            await progress_message.edit(content="✅ Temporary data has been cleaned from the database.")
        else:
            await progress_message.edit(content="❌ Failed to clean temporary data.")
    
    @app_commands.command(name="db_manage_backups", description="Manage database backups")
    @app_commands.default_permissions(administrator=True)
    async def db_manage_backups(self, interaction: discord.Interaction):
        """Manage database backups."""
        # Validate admin permissions (admin access only)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "db_manage_backups", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get all backups
        backups = self.db_manager.list_backups()
        
        if not backups:
            await interaction.followup.send("❌ No database backups found.", ephemeral=True)
            return
        
        # Get backup storage stats
        total_size_mb = sum(backup["size_mb"] for backup in backups)
        auto_backups = [b for b in backups if b["filename"].startswith("backup_")]
        manual_backups = [b for b in backups if not b["filename"].startswith("backup_")]
        
        # Create main embed
        main_embed = discord.Embed(
            title="Database Backup Management",
            description=f"Total backups: **{len(backups)}**\n"
                      f"Total size: **{total_size_mb:.2f} MB**\n"
                      f"Auto backups: **{len(auto_backups)}**\n"
                      f"Manual backups: **{len(manual_backups)}**\n\n"
                      f"Select an action below to manage your backups.",
            color=discord.Color.blue()
        )
        
        # Create action buttons
        class BackupActions(discord.ui.View):
            def __init__(self, cog, timeout=60):
                super().__init__(timeout=timeout)
                self.cog = cog
            
            @discord.ui.button(label="Create New Backup", style=discord.ButtonStyle.primary)
            async def create_backup(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                # Create modal for backup name
                class BackupNameModal(discord.ui.Modal, title="Create Database Backup"):
                    backup_name = discord.ui.TextInput(
                        label="Backup Name", 
                        placeholder="Enter a name for this backup (optional)",
                        required=False
                    )
                    
                    async def on_submit(self, modal_interaction: discord.Interaction):
                        await modal_interaction.response.defer(ephemeral=True)
                        
                        name = self.backup_name.value if self.backup_name.value else None
                        backup_path = self.cog.db_manager.create_backup(name)
                        
                        await modal_interaction.followup.send(
                            f"✅ Backup created successfully: `{os.path.basename(backup_path)}`", 
                            ephemeral=True
                        )
                
                await b_interaction.response.send_modal(BackupNameModal())
            
            @discord.ui.button(label="Prune Old Backups", style=discord.ButtonStyle.danger)
            async def prune_backups(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                await b_interaction.response.defer(ephemeral=True)
                
                self.cog.db_manager._prune_old_backups()
                
                await b_interaction.followup.send(
                    "✅ Old backups have been pruned according to retention policy.", 
                    ephemeral=True
                )
            
            @discord.ui.button(label="View All Backups", style=discord.ButtonStyle.secondary)
            async def view_backups(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                # Create an embed showing all backups
                backups = self.cog.db_manager.list_backups()
                
                embed = discord.Embed(
                    title="All Database Backups",
                    description=f"Total: {len(backups)} backups",
                    color=discord.Color.blue()
                )
                
                for i, backup in enumerate(backups):
                    # Display in groups of 10
                    if i < 10:
                        embed.add_field(
                            name=f"{i+1}. {backup['filename']}",
                            value=f"Created: {backup['created']}\nSize: {backup['size_mb']} MB",
                            inline=False
                        )
                
                if len(backups) > 10:
                    embed.set_footer(text=f"Showing 10/{len(backups)} backups. Use /db_list_backups to see all.")
                
                await b_interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Send the embed with action buttons
        view = BackupActions(self)
        await interaction.followup.send(embed=main_embed, view=view, ephemeral=True)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(DatabaseAdminCog(bot))
