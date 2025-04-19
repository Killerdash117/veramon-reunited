"""
Core Forms System for Veramon Reunited

This module contains the core logic for the Veramon forms system,
managing transformations, special form conditions, and stat modifiers.
"""

from typing import Dict, List, Optional, Tuple, Any
from src.utils.config_manager import get_config
from src.db.db import get_connection
from src.core.weather import get_weather_system

class FormsSystem:
    """
    Core forms system that handles all form transformation logic independent
    of the Discord interface.
    """
    
    @staticmethod
    async def get_available_forms(veramon_id: int) -> List[Dict[str, Any]]:
        """
        Get all available forms for a specific Veramon.
        
        Args:
            veramon_id: ID of the Veramon
            
        Returns:
            List[Dict]: List of available forms with their requirements
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT data
                FROM veramon
                WHERE id = ?
            """, (veramon_id,))
            
            result = cursor.fetchone()
            if not result:
                return []
                
            import json
            veramon_data = json.loads(result[0])
            
            return veramon_data.get('forms', [])
            
        except Exception as e:
            print(f"Error getting available forms: {e}")
            return []
        finally:
            conn.close()
            
    @staticmethod
    async def check_form_eligibility(
        capture_id: int,
        form_id: str,
        user_id: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a Veramon is eligible for a specific form transformation.
        
        Args:
            capture_id: ID of the captured Veramon
            form_id: ID of the form to check
            user_id: Optional user ID for permission checks
            
        Returns:
            Tuple containing:
            - bool: True if eligible for the form
            - Dict: Requirements status details
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get the Veramon and its data
            cursor.execute("""
                SELECT c.veramon_id, c.level, c.active_form, v.data
                FROM captures c
                JOIN veramon v ON c.veramon_id = v.id
                WHERE c.id = ?
            """, (capture_id,))
            
            result = cursor.fetchone()
            if not result:
                return False, {"error": "Veramon not found"}
                
            veramon_id, level, active_form, veramon_data = result
            
            # Parse the JSON data
            import json
            veramon_data = json.loads(veramon_data)
            
            # Find the form
            forms = veramon_data.get('forms', [])
            target_form = None
            
            for form in forms:
                if form.get('id') == form_id:
                    target_form = form
                    break
                    
            if not target_form:
                return False, {"error": "Form not available for this Veramon"}
                
            # Check if already in this form
            if active_form == form_id:
                return False, {"error": "Veramon is already in this form"}
                
            # Check requirements
            requirements = target_form.get('requirements', {})
            requirements_status = {}
            all_requirements_met = True
            
            # Level requirement
            if 'level' in requirements:
                req_level = requirements['level']
                requirements_status['level'] = {
                    'required': req_level,
                    'current': level,
                    'met': level >= req_level
                }
                
                if level < req_level:
                    all_requirements_met = False
                    
            # Item requirement
            if 'item' in requirements:
                req_item = requirements['item']
                
                # Check if user has the item (placeholder logic)
                has_item = True  # Would check user inventory in actual implementation
                
                requirements_status['item'] = {
                    'required': req_item,
                    'met': has_item
                }
                
                if not has_item:
                    all_requirements_met = False
                    
            # Time requirement
            if 'time' in requirements:
                import time
                from datetime import datetime
                
                req_time = requirements['time']
                current_hour = datetime.now().hour
                
                is_valid_time = False
                if req_time == 'day' and 6 <= current_hour < 20:
                    is_valid_time = True
                elif req_time == 'night' and (current_hour >= 20 or current_hour < 6):
                    is_valid_time = True
                    
                requirements_status['time'] = {
                    'required': req_time,
                    'current': 'day' if 6 <= current_hour < 20 else 'night',
                    'met': is_valid_time
                }
                
                if not is_valid_time:
                    all_requirements_met = False
                    
            # Weather requirement
            if 'weather' in requirements:
                req_weather = requirements['weather']
                weather_system = get_weather_system()
                
                # In an actual implementation, we'd get the user's current biome
                # For now, we'll use a placeholder
                current_biome = "forest"  # Placeholder
                current_weather = weather_system.get_weather(current_biome)
                
                is_valid_weather = current_weather == req_weather
                
                requirements_status['weather'] = {
                    'required': req_weather,
                    'current': current_weather,
                    'met': is_valid_weather
                }
                
                if not is_valid_weather:
                    all_requirements_met = False
                    
            return all_requirements_met, {
                "form_name": target_form.get('name', form_id),
                "requirements": requirements_status
            }
            
        except Exception as e:
            print(f"Error checking form eligibility: {e}")
            return False, {"error": f"Error checking eligibility: {e}"}
        finally:
            conn.close()
            
    @staticmethod
    async def transform_veramon(
        capture_id: int,
        form_id: str,
        user_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Transform a Veramon to a specific form.
        
        Args:
            capture_id: ID of the captured Veramon
            form_id: ID of the form to transform into
            user_id: ID of the Veramon's owner
            
        Returns:
            Tuple containing:
            - bool: True if transformation was successful
            - Dict: Updated Veramon data if successful, error details if not
        """
        # First check eligibility
        is_eligible, status = await FormsSystem.check_form_eligibility(capture_id, form_id, user_id)
        
        if not is_eligible:
            return False, status
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Update the capture with the new form
            cursor.execute("""
                UPDATE captures
                SET active_form = ?
                WHERE id = ? AND user_id = ?
            """, (form_id, capture_id, user_id))
            
            # Record the form change in history
            cursor.execute("""
                INSERT INTO form_change_history (
                    user_id, capture_id, from_form_id, 
                    to_form_id, changed_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (user_id, capture_id, 
                  cursor.execute("SELECT active_form FROM captures WHERE id = ?", (capture_id,)).fetchone()[0] or 'base', 
                  form_id))
            
            conn.commit()
            
            # Get updated Veramon data
            cursor.execute("""
                SELECT c.veramon_id, c.level, c.xp, c.nickname, c.active_form,
                       v.data
                FROM captures c
                JOIN veramon v ON c.veramon_id = v.id
                WHERE c.id = ? AND c.user_id = ?
            """, (capture_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return False, {"error": "Failed to get updated Veramon data"}
                
            veramon_id, level, xp, nickname, active_form, veramon_data = result
            
            # Parse the JSON data
            import json
            veramon_data = json.loads(veramon_data)
            
            return True, {
                'id': veramon_id,
                'data': veramon_data,
                'nickname': nickname,
                'level': level,
                'xp': xp,
                'active_form': active_form
            }
            
        except Exception as e:
            print(f"Error transforming Veramon: {e}")
            conn.rollback()
            return False, {"error": f"Error during transformation: {e}"}
        finally:
            conn.close()
            
    @staticmethod
    def get_form_stats(veramon_data: Dict[str, Any], form_id: Optional[str]) -> Dict[str, Any]:
        """
        Get the stats for a specific Veramon form.
        
        Args:
            veramon_data: Veramon data including base stats
            form_id: ID of the form (or None for base form)
            
        Returns:
            Dict: Modified stats for the form
        """
        if not form_id:
            return veramon_data.get('stats', {})
            
        # Get base stats
        base_stats = veramon_data.get('stats', {})
        
        # Find the form
        forms = veramon_data.get('forms', [])
        form_data = None
        
        for form in forms:
            if form.get('id') == form_id:
                form_data = form
                break
                
        if not form_data:
            return base_stats
            
        # Apply stat modifiers
        stat_modifiers = form_data.get('stat_modifiers', {})
        stat_modifier_cap = get_config("forms", "stat_modifier_cap", 2.0)
        
        modified_stats = base_stats.copy()
        
        for stat, value in base_stats.items():
            if stat in stat_modifiers:
                modifier = min(stat_modifiers[stat], stat_modifier_cap)
                modified_stats[stat] = int(value * modifier)
                
        return modified_stats

# Function to get a global instance
_forms_system = None

def get_forms_system():
    """
    Get the global forms system instance.
    
    Returns:
        FormsSystem: Global forms system instance
    """
    global _forms_system
    
    if _forms_system is None:
        _forms_system = FormsSystem()
        
    return _forms_system
