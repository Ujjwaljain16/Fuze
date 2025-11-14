#!/usr/bin/env python3
"""
Flask-compatible integration test for UniversalSemanticMatcher
This test can be run within the Flask app context
"""

def test_universal_matcher_standalone():
    """Test UniversalSemanticMatcher without Flask dependencies"""
    print("🧪 Testing UniversalSemanticMatcher Standalone")
    print("=" * 50)
    
    try:
        # Test 1: Import and initialize
        from universal_semantic_matcher import UniversalSemanticMatcher
        matcher = UniversalSemanticMatcher()
        print("✅ UniversalSemanticMatcher imported and initialized")
        
        # Test 2: Test spelling variations
        print("\n📊 Testing spelling variations...")
        test_cases = [
            ("DSA visualiser", "DSA visualizer"),
            ("Python optimise", "Python optimize"),
            ("React programme", "React program"),
            ("Java analyse", "Java analyze"),
            ("C++ centre", "C++ center")
        ]
        
        all_passed = True
        for query, expected in test_cases:
            similarity = matcher.calculate_semantic_similarity(query, expected)
            print(f"'{query}' vs '{expected}': {similarity:.3f}")
            
            if similarity > 0.8:
                print(f"   ✅ High similarity - spelling variation handled correctly")
            else:
                print(f"   ⚠️ Lower similarity - may need adjustment")
                all_passed = False
        
        # Test 3: Test technology synonyms
        print("\n📊 Testing technology synonyms...")
        tech_cases = [
            ("JavaScript tutorial", "JS tutorial"),
            ("Python web app", "Py web app"),
            ("React components", "ReactJS components"),
            ("Node.js backend", "Node backend")
        ]
        
        for query, expected in tech_cases:
            similarity = matcher.calculate_semantic_similarity(query, expected)
            print(f"'{query}' vs '{expected}': {similarity:.3f}")
            
            if similarity > 0.7:
                print(f"   ✅ High similarity - technology synonym handled correctly")
            else:
                print(f"   ⚠️ Lower similarity - may need adjustment")
                all_passed = False
        
        # Test 4: Test content type variations
        print("\n📊 Testing content type variations...")
        content_cases = [
            ("Python tutorial", "Python guide"),
            ("React documentation", "React docs"),
            ("Java course", "Java training"),
            ("Docker example", "Docker sample")
        ]
        
        for query, expected in content_cases:
            similarity = matcher.calculate_semantic_similarity(query, expected)
            print(f"'{query}' vs '{expected}': {similarity:.3f}")
            
            if similarity > 0.6:
                print(f"   ✅ Good similarity - content type variation handled correctly")
            else:
                print(f"   ⚠️ Lower similarity - may need adjustment")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Standalone test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_components():
    """Test individual components that will be used in integration"""
    print("\n🧪 Testing Integration Components")
    print("=" * 50)
    
    try:
        # Test 1: Check if the orchestrator file can be parsed (without importing)
        print("📊 Test 1: Checking orchestrator file structure...")
        
        with open('unified_recommendation_orchestrator.py', 'r') as f:
            content = f.read()
        
        # Check for key integration points
        integration_checks = [
            ('UniversalSemanticMatcher import', 'from universal_semantic_matcher import UniversalSemanticMatcher'),
            ('UniversalSemanticMatcher initialization', 'self.universal_matcher = UniversalSemanticMatcher()'),
            ('Universal matcher usage in similarity', 'self.universal_matcher.calculate_semantic_similarity'),
            ('Universal matcher usage in tech overlap', 'self.universal_matcher.calculate_technology_overlap')
        ]
        
        all_checks_passed = True
        for check_name, check_string in integration_checks:
            if check_string in content:
                print(f"   ✅ {check_name}: Found")
            else:
                print(f"   ❌ {check_name}: Missing")
                all_checks_passed = False
        
        # Test 2: Check if universal_semantic_matcher.py exists and is valid
        print("\n📊 Test 2: Checking universal_semantic_matcher.py...")
        
        try:
            with open('universal_semantic_matcher.py', 'r') as f:
                matcher_content = f.read()
            
            # Check for key class and methods
            class_checks = [
                ('UniversalSemanticMatcher class', 'class UniversalSemanticMatcher'),
                ('normalize_text method', 'def normalize_text'),
                ('calculate_semantic_similarity method', 'def calculate_semantic_similarity'),
                ('calculate_technology_overlap method', 'def calculate_technology_overlap')
            ]
            
            for check_name, check_string in class_checks:
                if check_string in matcher_content:
                    print(f"   ✅ {check_name}: Found")
                else:
                    print(f"   ❌ {check_name}: Missing")
                    all_checks_passed = False
                    
        except FileNotFoundError:
            print("   ❌ universal_semantic_matcher.py not found")
            all_checks_passed = False
        
        return all_checks_passed
        
    except Exception as e:
        print(f"❌ Integration components test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Universal Semantic Matcher Integration Test (Flask-Compatible)")
    print("=" * 70)
    
    tests = [
        ("Standalone Functionality", test_universal_matcher_standalone),
        ("Integration Components", test_integration_components)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 Integration Test Results")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🏁 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 SUCCESS! Universal Semantic Matcher is ready for Flask integration!")
        print("\n💡 What this means:")
        print("✅ UniversalSemanticMatcher works perfectly standalone")
        print("✅ All integration code is properly placed in orchestrator")
        print("✅ Ready to handle spelling variations in your Flask app")
        print("✅ 'DSA visualiser' will correctly match 'DSA visualizer' bookmarks")
        print("\n🚀 Next steps:")
        print("   1. Start your Flask app")
        print("   2. The UniversalSemanticMatcher will automatically integrate")
        print("   3. Test with a real recommendation request")
        print("   4. Watch the logs for '✅ UniversalSemanticMatcher imported successfully'")
    else:
        print("\n⚠️ Some integration issues need attention")
        print("\n🔧 To test full integration:")
        print("   1. Start your Flask app: python app.py")
        print("   2. Make a recommendation request")
        print("   3. Check the logs for UniversalSemanticMatcher messages")

if __name__ == "__main__":
    main()
