"""
Tests for the Research Ideas Pool module.

Verifies that:
1. All ideas are properly structured
2. Helper functions work correctly
3. LLM selection format is valid
4. Implementation prompts are generated correctly
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ea.knowledge.research_ideas_pool import (
    RESEARCH_IDEAS,
    ResearchIdea,
    get_ideas_by_category,
    get_ideas_by_difficulty,
    get_easy_wins,
    format_for_llm_selection,
    get_idea_by_id,
    get_implementation_prompt,
)


class TestResearchIdeasStructure:
    """Test that all research ideas are properly structured."""
    
    def test_ideas_not_empty(self):
        """Verify we have research ideas."""
        assert len(RESEARCH_IDEAS) > 0, "Research ideas pool should not be empty"
        print(f"鉁?Found {len(RESEARCH_IDEAS)} research ideas")
    
    def test_all_ideas_have_required_fields(self):
        """Verify all ideas have required fields."""
        required_fields = ['id', 'name', 'category', 'difficulty', 
                          'expected_f1_gain', 'summary', 'key_insight', 
                          'implementation_steps']
        
        for idea in RESEARCH_IDEAS:
            for field in required_fields:
                value = getattr(idea, field)
                assert value is not None, f"Idea {idea.id} missing {field}"
                if isinstance(value, str):
                    assert len(value) > 0, f"Idea {idea.id} has empty {field}"
                elif isinstance(value, list):
                    assert len(value) > 0, f"Idea {idea.id} has empty {field}"
        
        print(f"鉁?All {len(RESEARCH_IDEAS)} ideas have required fields")
    
    def test_unique_ids(self):
        """Verify all idea IDs are unique."""
        ids = [idea.id for idea in RESEARCH_IDEAS]
        assert len(ids) == len(set(ids)), "Duplicate idea IDs found"
        print(f"鉁?All {len(ids)} idea IDs are unique")
    
    def test_valid_difficulties(self):
        """Verify all difficulties are valid."""
        valid_difficulties = {'easy', 'medium', 'hard'}
        for idea in RESEARCH_IDEAS:
            assert idea.difficulty in valid_difficulties, \
                f"Idea {idea.id} has invalid difficulty: {idea.difficulty}"
        print(f"鉁?All difficulties are valid")
    
    def test_valid_categories(self):
        """Verify categories are consistent."""
        categories = set(idea.category for idea in RESEARCH_IDEAS)
        print(f"鉁?Found {len(categories)} categories: {categories}")
        assert len(categories) >= 3, "Should have at least 3 categories"


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_ideas_by_category(self):
        """Test filtering by category."""
        # Get all unique categories
        categories = set(idea.category for idea in RESEARCH_IDEAS)
        
        for category in categories:
            ideas = get_ideas_by_category(category)
            assert len(ideas) > 0, f"No ideas found for category: {category}"
            for idea in ideas:
                assert idea.category == category
        
        print(f"鉁?get_ideas_by_category works for all {len(categories)} categories")
    
    def test_get_ideas_by_difficulty(self):
        """Test filtering by difficulty."""
        for difficulty in ['easy', 'medium', 'hard']:
            ideas = get_ideas_by_difficulty(difficulty)
            for idea in ideas:
                assert idea.difficulty == difficulty
        
        print(f"鉁?get_ideas_by_difficulty works correctly")
    
    def test_get_easy_wins(self):
        """Test getting easy wins."""
        easy_wins = get_easy_wins()
        assert len(easy_wins) > 0, "Should have at least one easy win"
        for idea in easy_wins:
            assert idea.difficulty == 'easy'
        
        print(f"鉁?Found {len(easy_wins)} easy wins")
    
    def test_get_idea_by_id(self):
        """Test getting idea by ID."""
        # Test existing ID
        idea = get_idea_by_id("arch_transformer")
        assert idea is not None
        assert idea.id == "arch_transformer"
        
        # Test non-existing ID
        idea = get_idea_by_id("non_existing_id")
        assert idea is None
        
        print(f"鉁?get_idea_by_id works correctly")


class TestLLMInterface:
    """Test LLM interface functions."""
    
    def test_format_for_llm_selection_basic(self):
        """Test basic LLM selection format."""
        formatted = format_for_llm_selection()
        
        assert "RESEARCH IDEAS POOL" in formatted
        assert "Architecture" in formatted or "ARCHITECTURE" in formatted
        assert "Implementation Steps" in formatted
        assert "YOUR TASK" in formatted
        assert "selected_id" in formatted
        
        print(f"鉁?Basic LLM selection format is valid ({len(formatted)} chars)")
    
    def test_format_for_llm_selection_with_context(self):
        """Test LLM selection format with context."""
        formatted = format_for_llm_selection(
            current_approach="DIEN with Focal Loss",
            failed_approaches=["Multi-Interest Extraction"],
            plateau_length=5
        )
        
        assert "plateau length: 5" in formatted
        assert "DIEN with Focal Loss" in formatted
        
        print(f"鉁?LLM selection format with context is valid")
    
    def test_format_excludes_failed_approaches(self):
        """Test that failed approaches are excluded."""
        formatted = format_for_llm_selection(
            failed_approaches=["Transformer-Based Sequence Modeling"]
        )
        
        # The exact name should not appear as a header
        # (it might appear in the "Previously tried" list)
        lines = formatted.split('\n')
        header_lines = [l for l in lines if l.startswith('### [')]
        
        # Check that transformer idea is not in headers
        transformer_headers = [l for l in header_lines if 'arch_transformer' in l]
        assert len(transformer_headers) == 0, "Failed approach should be excluded"
        
        print(f"鉁?Failed approaches are properly excluded")
    
    def test_get_implementation_prompt(self):
        """Test implementation prompt generation."""
        prompt = get_implementation_prompt("loss_power_focal")
        
        assert "Power Focal Loss" in prompt
        assert "Implementation Steps" in prompt
        assert "Key Insight" in prompt
        assert "Reference Code" in prompt or "code" in prompt.lower()
        
        print(f"鉁?Implementation prompt generated correctly ({len(prompt)} chars)")
    
    def test_get_implementation_prompt_invalid_id(self):
        """Test implementation prompt for invalid ID."""
        prompt = get_implementation_prompt("invalid_id")
        assert "Unknown idea ID" in prompt
        
        print(f"鉁?Invalid ID handling works correctly")


class TestCodeSnippets:
    """Test that code snippets are valid Python."""
    
    def test_code_snippets_syntax(self):
        """Verify code snippets have valid Python syntax."""
        ideas_with_code = [idea for idea in RESEARCH_IDEAS if idea.code_snippet]
        
        for idea in ideas_with_code:
            try:
                # Try to compile the code snippet
                compile(idea.code_snippet, f"<{idea.id}>", 'exec')
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {idea.id} code snippet: {e}")
        
        print(f"鉁?All {len(ideas_with_code)} code snippets have valid syntax")


class TestCoverage:
    """Test coverage of different aspects."""
    
    def test_category_coverage(self):
        """Test that we have diverse categories."""
        categories = set(idea.category for idea in RESEARCH_IDEAS)
        
        expected_categories = {
            "Architecture",
            "Loss Function", 
            "Training Strategy",
            "Ensemble",
            "Feature Engineering"
        }
        
        for expected in expected_categories:
            assert expected in categories, f"Missing category: {expected}"
        
        print(f"鉁?All expected categories are covered")
    
    def test_difficulty_distribution(self):
        """Test that we have ideas at all difficulty levels."""
        difficulty_counts = {}
        for idea in RESEARCH_IDEAS:
            difficulty_counts[idea.difficulty] = difficulty_counts.get(idea.difficulty, 0) + 1
        
        assert 'easy' in difficulty_counts, "No easy ideas"
        assert 'medium' in difficulty_counts, "No medium ideas"
        assert 'hard' in difficulty_counts, "No hard ideas"
        
        print(f"鉁?Difficulty distribution: {difficulty_counts}")
    
    def test_has_actionable_steps(self):
        """Test that all ideas have actionable implementation steps."""
        for idea in RESEARCH_IDEAS:
            steps = idea.implementation_steps
            assert len(steps) >= 2, f"Idea {idea.id} needs more implementation steps"
            
            # Check that steps are numbered or structured
            first_step = steps[0]
            assert len(first_step) > 10, f"Idea {idea.id} has too short steps"
        
        print(f"鉁?All ideas have actionable implementation steps")


def run_all_tests():
    """Run all tests and print summary."""
    print("=" * 60)
    print("RESEARCH IDEAS POOL - TEST SUITE")
    print("=" * 60)
    print()
    
    test_classes = [
        TestResearchIdeasStructure,
        TestHelperFunctions,
        TestLLMInterface,
        TestCodeSnippets,
        TestCoverage,
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

