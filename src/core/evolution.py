"""
Core Evolution System for Veramon Reunited

This module contains the core logic for the Veramon evolution system,
separated from the Discord interface.
"""

from typing import Dict, List, Optional, Tuple, Any
from src.utils.config_manager import get_config
from src.db.db import get_connection

class EvolutionSystem:
    """
    Core evolution system that handles all evolution logic independent
    of the Discord interface.
    """
    
    @staticmethod
    def check_evolution_eligibility(
        veramon_id: int,
        veramon_level: int,
        evolution_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Check if a Veramon is eligible for evolution.
        
        Args:
            veramon_id: ID of the Veramon to check
            veramon_level: Current level of the Veramon
            evolution_data: Evolution requirements and paths
            
        Returns:
            Tuple containing:
            - bool: True if eligible for evolution
            - str: Evolution path ID if eligible, None otherwise
            - Dict: Evolution data if eligible, None otherwise
        """
        if not evolution_data or 'evolutions' not in evolution_data:
            return False, None, None
            
        available_evolutions = []
        
        for evolution in evolution_data['evolutions']:
            level_requirement = evolution.get('level_requirement', 0)
            
            # Check level requirement
            if veramon_level < level_requirement:
                continue
                
            # Check additional requirements
            requirements_met = True
            
            # Check specific requirements like items, time, etc.
            additional_reqs = evolution.get('requirements', {})
            
            if additional_reqs:
                # Implementation would check each requirement type
                # against the user's inventory, time of day, etc.
                pass
                
            if requirements_met:
                available_evolutions.append(evolution)
                
        if available_evolutions:
            # If multiple paths available, return the first one for now
            # In practice, this would be a choice for the user
            return True, available_evolutions[0]['id'], available_evolutions[0]
            
        return False, None, None
    
    @staticmethod
    async def evolve_veramon(
        user_id: str,
        capture_id: int,
        evolution_path_id: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Evolve a Veramon along a specific evolution path.
        
        Args:
            user_id: Owner of the Veramon
            capture_id: ID of the captured Veramon
            evolution_path_id: ID of the evolution path to follow
            
        Returns:
            Tuple containing:
            - bool: True if evolution was successful
            - Dict: New Veramon data if successful, None otherwise
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get the current Veramon data
            cursor.execute("""
                SELECT c.veramon_id, c.level, c.xp, c.nickname, c.active_form,
                       v.data
                FROM captures c
                JOIN veramon v ON c.veramon_id = v.id
                WHERE c.id = ? AND c.user_id = ?
            """, (capture_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return False, None
                
            veramon_id, level, xp, nickname, active_form, veramon_data = result
            
            # Parse veramon_data
            import json
            veramon_data = json.loads(veramon_data)
            
            # Find the evolution path
            evolution_data = veramon_data.get('evolution', {})
            target_evolution = None
            
            for evolution in evolution_data.get('evolutions', []):
                if evolution.get('id') == evolution_path_id:
                    target_evolution = evolution
                    break
                    
            if not target_evolution:
                return False, None
                
            # Get the evolved Veramon data
            evolved_veramon_id = target_evolution.get('evolves_to')
            
            cursor.execute("""
                SELECT id, data
                FROM veramon
                WHERE id = ?
            """, (evolved_veramon_id,))
            
            evolved_data = cursor.fetchone()
            if not evolved_data:
                return False, None
                
            new_veramon_id, new_veramon_data = evolved_data
            
            # Update the capture
            cursor.execute("""
                UPDATE captures
                SET veramon_id = ?, evolution_date = datetime('now')
                WHERE id = ? AND user_id = ?
            """, (new_veramon_id, capture_id, user_id))
            
            # Record the evolution in history
            cursor.execute("""
                INSERT INTO evolution_history (
                    user_id, capture_id, from_veramon_id, 
                    to_veramon_id, evolution_path, level
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, capture_id, veramon_id, new_veramon_id, 
                  evolution_path_id, level))
            
            conn.commit()
            
            # Return the new Veramon data
            new_veramon_data = json.loads(new_veramon_data)
            return True, {
                'id': new_veramon_id,
                'data': new_veramon_data,
                'nickname': nickname,
                'level': level,
                'xp': xp,
                'active_form': active_form
            }
            
        except Exception as e:
            print(f"Error evolving Veramon: {e}")
            conn.rollback()
            return False, None
        finally:
            conn.close()
    
    @staticmethod
    async def change_form(
        user_id: str,
        capture_id: int,
        form_id: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Change a Veramon's form.
        
        Args:
            user_id: Owner of the Veramon
            capture_id: ID of the captured Veramon
            form_id: ID of the form to change to
            
        Returns:
            Tuple containing:
            - bool: True if form change was successful
            - Dict: Updated Veramon data if successful, None otherwise
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get the current Veramon data
            cursor.execute("""
                SELECT c.veramon_id, c.level, c.xp, c.nickname, c.active_form,
                       v.data
                FROM captures c
                JOIN veramon v ON c.veramon_id = v.id
                WHERE c.id = ? AND c.user_id = ?
            """, (capture_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return False, None
                
            veramon_id, level, xp, nickname, active_form, veramon_data = result
            
            # Parse veramon_data
            import json
            veramon_data = json.loads(veramon_data)
            
            # Check if the form exists for this Veramon
            forms = veramon_data.get('forms', [])
            target_form = None
            
            for form in forms:
                if form.get('id') == form_id:
                    target_form = form
                    break
                    
            if not target_form:
                return False, None
                
            # Check if the form has requirements
            form_requirements = target_form.get('requirements', {})
            
            if form_requirements:
                # Implementation would check each requirement type
                # against various conditions like items, time, etc.
                pass
                
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
            """, (user_id, capture_id, active_form or 'base', form_id))
            
            conn.commit()
            
            # Return the updated data
            return True, {
                'id': veramon_id,
                'data': veramon_data,
                'nickname': nickname,
                'level': level,
                'xp': xp,
                'active_form': form_id
            }
            
        except Exception as e:
            print(f"Error changing Veramon form: {e}")
            conn.rollback()
            return False, None
        finally:
            conn.close()
