# Tests

Test suite for Ontario Damages Compendium.

## Running Tests

### Individual Test Files

```bash
# Test PDF report generation
python tests/test_pdf_report_generator.py

# Test inflation adjustment
python tests/test_inflation_adjuster.py

# Test anatomical mappings
python tests/test_anatomical_mappings.py

# Test expert report analyzer
python tests/test_expert_report_analyzer.py
```

### All Tests

```bash
# Run all tests
for test in tests/test_*.py; do
    echo "Running $test..."
    python "$test"
    echo ""
done
```

## Test Files

- **test_pdf_report_generator.py** - Tests PDF report generation with sample data
- **test_inflation_adjuster.py** - Tests CPI inflation calculations
- **test_anatomical_mappings.py** - Tests anatomical term to region mapping
- **test_expert_report_analyzer.py** - Tests expert report PDF analysis

## Adding New Tests

1. Create a new file: `tests/test_<module_name>.py`
2. Import the module to test
3. Write test functions
4. Add `if __name__ == "__main__"` block to allow standalone execution

## Future Enhancements

- [ ] Add pytest framework
- [ ] Add test fixtures
- [ ] Add code coverage reporting
- [ ] Add CI/CD integration
- [ ] Add integration tests
