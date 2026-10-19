"""
Tests for Research Ideas Pool integration with ResearchDirector.

Verifies that:
1. ResearchDirector can use the new research ideas pool
2. Selection works correctly with heuristics
3. Forced exploration prompts are generated correctly
4. Integration with runner.py works
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ea.knowledge.research_director import (
    ResearchDirector,
    ResearchDirection,
    RESEARCH_DIRECTIONS,
)
from ea.knowledge.research_ideas_pool import (
    RESEARCH_IDEAS,
    ResearchIdea,
    format_for_llm_selection,
    get_idea_by_id,
)


class TestResearchDirectorIntegration:
    """Test ResearchDirector integration with research ideas pool."""
    
    def test_director_initialization_with_pool(self):
        """Test that director initializes with new pool."""
        director = ResearchDirector(llm_client=None, use_new_pool=True)
        assert director.use_new_pool == True
        assert hasattr(director, '_idea_map')
        assert len(director._idea_map) == len(RESEARCH_IDEAS)
        print(f"鉁?Director initialized with {len(director._idea_map)} ideas from pool")
    
    def test_director_initialization_without_pool(self):
        """Test that director can work without new pool."""
        director = ResearchDirector(llm_client=None, use_new_pool=False)
        assert director.use_new_pool == False
        print(f"鉁?Director initialized without pool, using {len(director.directions)} legacy directions")
    
    def test_heuristic_selection_from_pool(self):
        """Test heuristic selection from research ideas pool."""
        director = ResearchDirector(llm_client=None, use_new_pool=True)
        
        # Test with short plateau (should prefer easy)
        result = director._heuristic_selection_from_pool(
            failed_approaches=[],
            plateau_length=5
        )
        assert 'direction' in result
        assert 'idea' in result
        assert result['idea'].difficulty == 'easy'
        print(f"鉁?Short plateau selected: {result['idea'].name} (difficulty: {result['idea'].difficulty})")
        
        # Test with long plateau (should prefer medium)
        result = director._heuristic_selection_from_pool(
            failed_approaches=[],
            plateau_length=12
        )
        assert result['idea'].difficulty in ['medium', 'easy']
        print(f"鉁?Long plateau selected: {result['idea'].name} (difficulty: {result['idea'].difficulty})")
    
    def test_heuristic_excludes_failed_approaches(self):
        """Test that heuristic excludes failed approaches."""
        director = ResearchDirector(llm_client=None, use_new_pool=True)
        
        # Mark "Transformer" as failed
        result = director._heuristic_selection_from_pool(
            failed_approaches=["Transformer-Based Sequence Modeling"],
            plateau_length=5
        )
        
        # Should not select transformer
        assert "transformer" not in result['idea'].name.lower()
        print(f"鉁?Excluded failed approach, selected: {result['idea'].name}")
    
    def test_select_direction_uses_pool(self):
        """Test that select_direction uses the new pool."""
        director = ResearchDirector(llm_client=None, use_new_pool=True)
        
        result = director.select_direction(
            best_f1=0.65,
            plateau_length=15,
            failed_approaches=[],
            current_code_summary="DIEN model with Focal Loss",
            performance_history=[0.60, 0.62, 0.64, 0.65, 0.65]
        )
        
        assert 'direction' in result
        assert 'idea' in result
        assert result['idea'] is not None
        print(f"鉁?select_direction returned: {result['idea'].name}")
    
    def test_forced_exploration_prompt_from_pool(self):
        """Test forced exploration prompt generation from pool."""
        director = ResearchDirector(llm_client=None, use_new_pool=True)
        
        result = director.select_direction(
            best_f1=0.65,
            plateau_length=15,
            failed_approaches=[],
            current_code_summary="DIEN model",
            performance_history=[0.65, 0.65, 0.65]
        )
        
        prompt = director.get_forced_exploration_prompt(result)
        
        assert "FORCED EXPLORATION MODE" in prompt
        assert result['idea'].name in prompt
        assert "CRITICAL REQUIREMENTS" in prompt
        print(f"鉁?Forced exploration prompt generated ({len(prompt)} chars)")
    
    def test_idea_to_direction_conversion(self):
        """Test conversion from ResearchIdea to ResearchDirection."""
        director = ResearchDirector(llm_client=None, use_new_pool=True)
        
        idea = get_idea_by_id("arch_transformer")
        direction = director._idea_to_direction(idea)
        
        assert isinstance(direction, ResearchDirection)
        assert direction.name == idea.name
        assert direction.category == idea.category
        assert direction.difficulty == idea.difficulty
        print(f"鉁?Converted {idea.name} to ResearchDirection")
    
    def test_selection_history_tracking(self):
        """Test that selection history is tracked."""
        director = ResearchDirector(llm_client=None, use_new_pool=True)
        
        # Make two selections
        director.select_direction(
            best_f1=0.65,
            plateau_length=10,
            failed_approaches=[],
            current_code_summary="Test 1",
            performance_history=[0.65]
        )
        
        director.select_direction(
            best_f1=0.66,
            plateau_length=5,
            failed_approaches=["Previous approach"],
            current_code_summary="Test 2",
            performance_history=[0.66]
        )
        
        assert len(director.selection_history) == 2
        assert director.selection_history[0]['best_f1'] == 0.65
        assert director.selection_history[1]['best_f1'] == 0.66
        print(f"鉁?Selection history tracked: {len(director.selection_history)} entries")


class TestFormatForLLMSelection:
    """Test the format_for_llm_selection function."""
    
    def test_basic_format(self):
        """Test basic formatting."""
        formatted = format_for_llm_selection()
        
        assert "RESEARCH IDEAS POOL" in formatted
        assert "ARCHITECTURE" in formatted.upper()  # Check uppercase version
        assert "selected_id" in formatted
        print(f"鉁?Basic format generated ({len(formatted)} chars)")
    
    def test_format_with_context(self):
        """Test formatting with context."""
        formatted = format_for_llm_selection(
            current_approach="DIEN with GRU",
            failed_approaches=["Simple MLP"],
            plateau_length=10
        )
        
        assert "plateau length: 10" in formatted
        assert "DIEN with GRU" in formatted
        assert "Simple MLP" in formatted
        print(f"鉁?Format with context generated")
    
    def test_format_excludes_failed(self):
        """Test that failed approaches are excluded from selection options."""
        # Get a specific idea name to mark as failed
        idea_to_fail = RESEARCH_IDEAS[0].name
        
        formatted = format_for_llm_selection(
            failed_approaches=[idea_to_fail]
        )
        
        # The failed idea should not appear as a selectable option
        # (it might appear in the "Previously tried" list though)
        lines = formatted.split('\n')
        header_lines = [l for l in lines if l.startswith('### [')]
        
        # Check that the failed idea is not in headers
        failed_in_headers = any(idea_to_fail in l for l in header_lines)
        assert not failed_in_headers, f"Failed approach {idea_to_fail} should be excluded"
        print(f"鉁?Failed approach excluded from options")


class TestBackwardsCompatibility:
    """Test backwards compatibility with legacy system."""
    
    def test_legacy_directions_still_work(self):
        """Test that legacy RESEARCH_DIRECTIONS still work."""
        director = ResearchDirector(llm_client=None, use_new_pool=False)
        
        result = director.select_direction(
            best_f1=0.65,
            plateau_length=15,
            failed_approaches=[],
            current_code_summary="Test",
            performance_history=[0.65]
        )
        
        assert 'direction' in result
        assert isinstance(result['direction'], ResearchDirection)
        print(f"鉁?Legacy selection works: {result['direction'].name}")
    
    def test_legacy_prompt_generation(self):
        """Test legacy prompt generation."""
        director = ResearchDirector(llm_client=None, use_new_pool=False)
        
        result = director._heuristic_selection(
            failed_approaches=[],
            plateau_length=10
        )
        
        prompt = director.get_forced_exploration_prompt(result)
        assert "FORCED EXPLORATION MODE" in prompt
        print(f"鉁?Legacy prompt generated")


def run_all_tests():
    """Run all tests and print summary."""
    print("=" * 60)
    print("RESEARCH INTEGRATION - TEST SUITE")
    print("=" * 60)
    print()
    
    test_classes = [
        TestResearchDirectorIntegration,
        TestFormatForLLMSelection,
        TestBackwardsCompatibility,
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n馃搵 {test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    getattr(instance, method_name)()
                    total_passed += 1
                except Exception as e:
                    print(f"鉂?{method_name}: {e}")
                    total_failed += 1
    
    print()
    print("=" * 60)
    print(f"SUMMARY: {total_passed} passed, {total_failed} failed")
    print("=" * 60)
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

