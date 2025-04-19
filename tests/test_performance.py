import unittest
import sys
import os
import time
import asyncio
import json
from unittest.mock import patch, MagicMock
import random

# Add the src directory to the system path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.veramon import Veramon
from src.cogs.catching_cog import CatchingCog, WeatherType, TimeOfDay

class TestSystemPerformance(unittest.TestCase):
    """Performance and stress tests for the Veramon Reunited system."""
    
    def setUp(self):
        """Set up test data."""
        # Create a mock bot
        self.mock_bot = MagicMock()
        
        # Test data for Veramon
        with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'veramon', 'eledragon.json'), 'r') as f:
            self.test_veramon_data = {"Eledragon": json.loads(f.read())}
        
        # Create a test instance of CatchingCog
        with patch('src.cogs.catching_cog.load_all_veramon_data', return_value=self.test_veramon_data), \
             patch('src.cogs.catching_cog.load_items_data', return_value={}), \
             patch('src.cogs.catching_cog.load_biomes_data', return_value=self.get_test_biomes()):
            self.cog = CatchingCog(self.mock_bot)
    
    def get_test_biomes(self):
        """Get test biome data with many spawn entries for stress testing."""
        # Generate a large number of spawn entries for stress testing
        common_spawns = [f"CommonTestMon{i}" for i in range(100)]
        uncommon_spawns = [f"UncommonTestMon{i}" for i in range(50)]
        rare_spawns = [f"RareTestMon{i}" for i in range(20)]
        legendary_spawns = [f"LegendaryTestMon{i}" for i in range(5)]
        
        return {
            "stress_test_biome": {
                "name": "Stress Test Biome",
                "description": "A biome for stress testing",
                "weather_effects": {
                    "sunny": {
                        "description": "Sunny day in test biome",
                        "spawn_modifiers": {
                            "Fire": 1.5,
                            "Water": 0.7
                        },
                        "encounter_rate": 1.2
                    },
                    "rainy": {
                        "description": "Rainy day in test biome",
                        "spawn_modifiers": {
                            "Water": 1.8,
                            "Fire": 0.5
                        },
                        "encounter_rate": 0.9
                    },
                    "foggy": {
                        "description": "Foggy day in test biome",
                        "spawn_modifiers": {
                            "Ghost": 1.6,
                            "Normal": 0.8
                        },
                        "encounter_rate": 0.8
                    },
                    "thunderstorm": {
                        "description": "Thunderstorm in test biome",
                        "spawn_modifiers": {
                            "Electric": 2.0,
                            "Flying": 0.4
                        },
                        "encounter_rate": 1.3
                    }
                },
                "time_effects": {
                    "morning": {
                        "description": "Morning in test biome",
                        "spawn_modifiers": {
                            "Normal": 1.3
                        }
                    },
                    "day": {
                        "description": "Day in test biome",
                        "spawn_modifiers": {
                            "Fire": 1.2
                        }
                    },
                    "evening": {
                        "description": "Evening in test biome",
                        "spawn_modifiers": {
                            "Bug": 1.4
                        }
                    },
                    "night": {
                        "description": "Night in test biome",
                        "spawn_modifiers": {
                            "Dark": 1.7,
                            "Ghost": 1.5
                        }
                    }
                },
                "special_areas": [
                    {
                        "id": f"test_special_area_{i}",
                        "name": f"Test Special Area {i}",
                        "description": f"A special area for testing #{i}",
                        "unlock_requirement": {
                            "type": "achievement",
                            "id": f"test_achievement_{i}"
                        },
                        "spawn_table": {
                            "rare": rare_spawns,
                            "legendary": legendary_spawns
                        },
                        "encounter_rate": 1.5
                    } for i in range(20)  # Create 20 special areas
                ],
                "spawn_table": {
                    "common": common_spawns,
                    "uncommon": uncommon_spawns,
                    "rare": rare_spawns,
                    "legendary": legendary_spawns
                }
            }
        }
    
    def test_evolution_performance(self):
        """Test the performance of evolution path checking with many evolution paths."""
        # Create a Veramon with many evolution paths for stress testing
        evolution_paths = [
            {
                "evolves_to": f"TestEvolution{i}",
                "level_required": 20 + i,
                "description": f"Evolves when reaching level {20 + i}"
            } for i in range(100)  # 100 possible evolution paths
        ]
        
        test_data = {
            "name": "PerformanceTestMon",
            "type": ["Normal"],
            "base_stats": {
                "hp": 70,
                "atk": 85,
                "def": 60,
                "sp_atk": 95,
                "sp_def": 70,
                "speed": 90
            },
            "evolution": {
                "paths": evolution_paths
            }
        }
        
        # Create the test Veramon
        test_veramon = Veramon(name="PerformanceTestMon", data=test_data, level=50)
        
        # Measure performance of evolution checking
        start_time = time.time()
        iterations = 1000
        
        for _ in range(iterations):
            can_evolve, evolves_to = test_veramon.can_evolve()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Evolution path checking: {iterations} iterations in {duration:.4f} seconds")
        print(f"Average time per check: {(duration/iterations)*1000:.4f} ms")
        
        # The test passes if it completes within a reasonable time
        # For example, each evolution check should take less than 1ms on average
        self.assertLess(duration/iterations, 0.001)
    
    def test_form_transformation_performance(self):
        """Test the performance of form checking and transformation with many forms."""
        # Create a Veramon with many forms for stress testing
        forms = [
            {
                "id": f"test_form_{i}",
                "name": f"Test Form {i}",
                "description": f"Test form #{i}",
                "stat_modifiers": {
                    "sp_atk": 1.2,
                    "speed": 1.1
                },
                "level_required": 10
            } for i in range(100)  # 100 possible forms
        ]
        
        test_data = {
            "name": "FormTestMon",
            "type": ["Normal"],
            "base_stats": {
                "hp": 70,
                "atk": 85,
                "def": 60,
                "sp_atk": 95,
                "sp_def": 70,
                "speed": 90
            },
            "forms": forms
        }
        
        # Create the test Veramon
        test_veramon = Veramon(name="FormTestMon", data=test_data, level=20)
        
        # Measure performance of form checking
        start_time = time.time()
        iterations = 1000
        
        for _ in range(iterations):
            available_forms = test_veramon.get_available_forms()
            if available_forms:
                test_veramon.transform_to_form(available_forms[0]["id"])
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Form checking and transformation: {iterations} iterations in {duration:.4f} seconds")
        print(f"Average time per operation: {(duration/iterations)*1000:.4f} ms")
        
        # The test passes if it completes within a reasonable time
        # For example, each form operation should take less than 2ms on average
        self.assertLess(duration/iterations, 0.002)
    
    def test_weather_update_performance(self):
        """Test the performance of weather updates with many biomes."""
        # Create a large number of biomes for stress testing
        large_biomes = {}
        for i in range(100):  # 100 biomes
            large_biomes[f"biome_{i}"] = {
                "name": f"Biome {i}",
                "description": f"Test biome #{i}",
                "weather_effects": {
                    "sunny": {"description": "Sunny", "encounter_rate": 1.0},
                    "rainy": {"description": "Rainy", "encounter_rate": 0.9},
                    "foggy": {"description": "Foggy", "encounter_rate": 0.8},
                    "windy": {"description": "Windy", "encounter_rate": 1.1}
                }
            }
        
        # Patch the CatchingCog to use our large biomes set
        with patch.object(self.cog, 'biomes', large_biomes):
            # Force a weather update
            self.cog.last_weather_update = 0
            
            # Measure performance
            start_time = time.time()
            iterations = 10
            
            for _ in range(iterations):
                self.cog._update_weather()
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Weather update for {len(large_biomes)} biomes: {iterations} iterations in {duration:.4f} seconds")
            print(f"Average time per update: {(duration/iterations)*1000:.4f} ms")
            
            # The test passes if it completes within a reasonable time
            # Weather updates can be slower as they happen less frequently
            self.assertLess(duration/iterations, 0.5)  # 500ms per update is reasonable
    
    @patch('random.random')
    def test_spawn_table_performance(self, mock_random):
        """Test the performance of spawn table processing with weather and time modifiers."""
        # Fix random value to ensure consistent test behavior
        mock_random.return_value = 0.3  # Ensure encounters happen
        
        # Set up test conditions
        self.cog.current_weather["stress_test_biome"] = "sunny"
        
        # Veramon types for testing type modifiers
        for i in range(200):
            type1 = random.choice(["Fire", "Water", "Electric", "Ground", "Flying", "Bug", "Dark", "Ghost"])
            type2 = random.choice(["Normal", "Fighting", "Poison", "Rock", "Steel", "Ice", "Dragon", "Fairy", None])
            types = [type1]
            if type2:
                types.append(type2)
            
            self.cog.veramon_data[f"TestMon{i}"] = {
                "name": f"TestMon{i}",
                "type": types,
                "rarity": random.choice(["common", "uncommon", "rare", "legendary", "mythic"]),
                "shiny_rate": 0.01,
                "catch_rate": random.randint(5, 100)
            }
        
        # Time setup would be part of a real test
        with patch('src.cogs.catching_cog.TimeOfDay') as mock_time:
            mock_time.MORNING = TimeOfDay.MORNING
            mock_time.DAY = TimeOfDay.DAY
            mock_time.EVENING = TimeOfDay.EVENING
            mock_time.NIGHT = TimeOfDay.NIGHT
            
            # In a real test, we would measure the performance of the explore method itself
            # but since it requires Discord interaction objects, we'll simulate the
            # relevant parts of the spawn table processing instead
            
            start_time = time.time()
            iterations = 100
            
            for _ in range(iterations):
                # Simulate the core spawn selection logic from explore
                biome_key = "stress_test_biome"
                biome_data = self.cog.biomes[biome_key]
                spawn_table = biome_data.get('spawn_table', {})
                current_weather = self.cog.current_weather.get(biome_key)
                time_of_day = self.cog._get_current_time_of_day()
                
                # Apply weather modifiers
                spawn_modifiers = {}
                if current_weather and current_weather in biome_data.get('weather_effects', {}):
                    weather_data = biome_data['weather_effects'][current_weather]
                    spawn_modifiers = weather_data.get('spawn_modifiers', {})
                
                # Apply time modifiers
                if time_of_day.value in biome_data.get('time_effects', {}):
                    time_data = biome_data['time_effects'][time_of_day.value]
                    time_modifiers = time_data.get('spawn_modifiers', {})
                    for type_name, modifier in time_modifiers.items():
                        if type_name in spawn_modifiers:
                            spawn_modifiers[type_name] *= modifier
                        else:
                            spawn_modifiers[type_name] = modifier
                
                # Process the spawn table
                choices = []
                for rarity, names in spawn_table.items():
                    weight = self.cog.RARITY_WEIGHTS.get(rarity.lower(), 1)
                    for name in names:
                        if name in self.cog.veramon_data:
                            veramon_types = self.cog.veramon_data[name].get('type', [])
                            
                            # Apply type-based modifiers
                            type_modifier = 1.0
                            for vtype in veramon_types:
                                if vtype in spawn_modifiers:
                                    type_modifier *= spawn_modifiers[vtype]
                            
                            adjusted_weight = weight * type_modifier
                            choices.append((name, adjusted_weight))
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Spawn table processing: {iterations} iterations in {duration:.4f} seconds")
            print(f"Average time per process: {(duration/iterations)*1000:.4f} ms")
            
            # The test passes if it completes within a reasonable time
            self.assertLess(duration/iterations, 0.05)  # 50ms per spawn table processing is reasonable


if __name__ == '__main__':
    unittest.main()
