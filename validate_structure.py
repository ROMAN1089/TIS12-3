"""
Simple validation script to test imports and basic structure.
This script validates that all modules can be imported without errors.
"""
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test config module
        from orchestrator.config import Settings, settings
        print("✓ config.py imports successfully")
        print(f"  - Temporal host: {settings.temporal_host}")
        print(f"  - Task queue: {settings.temporal_task_queue}")
        
        # Test activities module
        from orchestrator.activities import AgentActivities
        print("✓ activities.py imports successfully")
        
        # Test workflow module
        from orchestrator.workflow import MultiAgentWorkflow
        print("✓ workflow.py imports successfully")
        
        # Test worker module
        from orchestrator.worker import setup_logging
        print("✓ worker.py imports successfully")
        
        # Test package init
        from orchestrator import __version__
        print(f"✓ orchestrator package initialized (version: {__version__})")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_structure():
    """Test configuration structure."""
    print("\nTesting configuration structure...")
    
    try:
        from orchestrator.config import Settings
        
        # Create a test settings instance
        test_settings = Settings(
            service_token="test-token",
            temporal_host="test:7233"
        )
        
        print("✓ Settings can be instantiated")
        
        # Test get_agent_token method
        token = test_settings.get_agent_token("decomposer")
        assert token == "test-token", "get_agent_token should return service_token as fallback"
        print("✓ get_agent_token method works correctly")
        
        print("\n✅ Configuration structure validated!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_activities_structure():
    """Test activities structure."""
    print("\nTesting activities structure...")
    
    try:
        from orchestrator.activities import AgentActivities
        
        activities = AgentActivities()
        
        # Check that methods exist
        assert hasattr(activities, 'call_decomposer'), "call_decomposer method missing"
        assert hasattr(activities, 'call_executor'), "call_executor method missing"
        assert hasattr(activities, 'call_validator'), "call_validator method missing"
        assert hasattr(activities, '_call_agent'), "_call_agent method missing"
        
        print("✓ All activity methods exist")
        print("\n✅ Activities structure validated!")
        return True
        
    except Exception as e:
        print(f"\n❌ Activities test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Orchestrator Structure Validation")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config_structure()))
    results.append(("Activities", test_activities_structure()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All validation tests passed!")
        return 0
    else:
        print("\n⚠️  Some validation tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
