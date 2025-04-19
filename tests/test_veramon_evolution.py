import unittest
import sys
import os
import json

# Add the src directory to the system path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.veramon import Veramon

class TestVeramonEvolution(unittest.TestCase):
    """Test cases for the Veramon evolution system."""
    
    def setUp(self):
        """Set up test data."""
        # Create test Veramon data
        self.test_data = {
            "name": "TestVeramon",
            "type": ["Electric", "Dragon"],
            "base_stats": {
                "hp": 70,
                "atk": 85,
                "def": 60,
                "sp_atk": 95,
                "sp_def": 70,
                "speed": 90
            },
            "evolution": {
                "paths": [
                    {
                        "evolves_to": "TestEvolution1",
                        "level_required": 30,
                        "description": "Evolves when reaching level 30"
                    },
                    {
                        "evolves_to": "TestEvolution2",
                        "required_item": "test_stone",
                        "level_required": 25,
                        "description": "Evolves when exposed to a Test Stone after level 25"
                    }
                ]
            },
            "forms": [
                {
                    "id": "test_form_1",
                    "name": "Test Form 1",
                    "description": "A test form",
                    "stat_modifiers": {
                        "sp_atk": 1.5,
                        "speed": 1.2
                    },
                    "level_required": 20
                },
                {
                    "id": "test_form_2",
                    "name": "Test Form 2",
                    "description": "Another test form",
                    "stat_modifiers": {
                        "hp": 1.3,
                        "def": 1.4
                    },
                    "required_item": "test_orb"
                }
            ]
        }
        
        # Create a test Veramon instance
        self.veramon = Veramon(
            name="TestVeramon",
            data=self.test_data,
            level=1
        )
        
    def test_evolution_level_requirement(self):
        """Test that Veramon doesn't evolve until it reaches the required level."""
        # At level 1, should not evolve
        can_evolve, _ = self.veramon.can_evolve()
        self.assertFalse(can_evolve)
        
        # Set level to just below evolution threshold
        self.veramon.level = 29
        can_evolve, _ = self.veramon.can_evolve()
        self.assertFalse(can_evolve)
        
        # Set level to evolution threshold
        self.veramon.level = 30
        can_evolve, evolves_to = self.veramon.can_evolve()
        self.assertTrue(can_evolve)
        self.assertEqual(evolves_to, "TestEvolution1")
        
    def test_multiple_evolution_paths(self):
        """Test that the correct evolution path is selected based on requirements."""
        # At level 25, it should be eligible for item-based evolution but not level-based
        self.veramon.level = 25
        can_evolve, _ = self.veramon.can_evolve()
        
        # Without the item, it shouldn't evolve even at level 25
        self.assertFalse(can_evolve)
        
        # If we had item checking implemented, we would add tests for item-based evolution here
        
        # At level 30, level-based evolution should be available
        self.veramon.level = 30
        can_evolve, evolves_to = self.veramon.can_evolve()
        self.assertTrue(can_evolve)
        self.assertEqual(evolves_to, "TestEvolution1")
        
    def test_forms_availability(self):
        """Test that forms are correctly identified as available based on requirements."""
        # At level 1, no forms should be available
        forms = self.veramon.get_available_forms()
        self.assertEqual(len(forms), 0)
        
        # At level 20, only the level-based form should be available
        self.veramon.level = 20
        forms = self.veramon.get_available_forms()
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]["id"], "test_form_1")
        
        # Test form transformation
        can_transform = self.veramon.transform_to_form("test_form_1")
        self.assertTrue(can_transform)
        self.assertEqual(self.veramon.active_form, "test_form_1")
        
        # Test invalid form transformation
        can_transform = self.veramon.transform_to_form("nonexistent_form")
        self.assertFalse(can_transform)
        
    def test_evolution_after_form_change(self):
        """Test that Veramon can still evolve after changing forms."""
        # Set level to evolution threshold and transform
        self.veramon.level = 30
        self.veramon.transform_to_form("test_form_1")
        
        # Check if can still evolve
        can_evolve, evolves_to = self.veramon.can_evolve()
        self.assertTrue(can_evolve)
        self.assertEqual(evolves_to, "TestEvolution1")
        
if __name__ == '__main__':
    unittest.main()
