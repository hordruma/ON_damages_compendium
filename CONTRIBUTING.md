# Contributing to Ontario Damages Compendium

Thank you for considering contributing to this project! This tool helps legal professionals find comparable personal injury cases more efficiently.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Check if the issue already exists in [GitHub Issues](https://github.com/hordruma/ON_damages_compendium/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Screenshots if applicable
   - Your environment (OS, Python version, etc.)

### Suggesting Enhancements

We welcome suggestions for:
- New anatomical regions
- Improved search algorithms
- Better UI/UX
- Performance optimizations
- Additional features

Open an issue with the "enhancement" label and describe:
- The problem you're solving
- Your proposed solution
- Alternative solutions considered
- Any mockups or examples

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/ON_damages_compendium.git
cd ON_damages_compendium
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## Making Changes

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Keep functions focused and single-purpose

### Testing

Before submitting:

1. Test the extraction notebook with sample data
2. Test the Streamlit app locally
3. Verify all regions are clickable
4. Test search with various inputs
5. Check for console errors

### Documentation

Update documentation if you:
- Add new features
- Change existing functionality
- Add new dependencies
- Modify region mappings

## Pull Request Process

### 1. Ensure Quality

- [ ] Code follows project style
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Commit messages are clear

### 2. Submit PR

1. Push your branch to your fork
2. Open a Pull Request to `main`
3. Fill out the PR template
4. Link related issues
5. Request review

### 3. PR Review

- Maintainers will review within 1 week
- Address any requested changes
- Once approved, we'll merge

### 4. After Merge

- Delete your branch
- Pull latest main
- Start next contribution!

## Areas for Contribution

### High Priority

1. **Improved PDF Extraction**
   - Better table parsing
   - Handle edge cases
   - Extract more metadata

2. **Enhanced Search**
   - Better region matching
   - Consider case age
   - Weight by jurisdiction

3. **UI Improvements**
   - Better body diagrams
   - Mobile responsiveness
   - Accessibility features

4. **Performance**
   - Faster embedding generation
   - Optimize search algorithm
   - Reduce memory usage

### Medium Priority

1. **Additional Features**
   - Export search results
   - Case comparison tool
   - Historical trends
   - Plaintiff demographic filters

2. **Data Quality**
   - Validate extracted cases
   - Improve region mappings
   - Add case verification

3. **Documentation**
   - Video tutorials
   - API documentation
   - Legal usage guide

### Low Priority

1. **Nice to Have**
   - Dark mode
   - Keyboard shortcuts
   - Search history
   - Saved searches

## Specific Contribution Guides

### Adding a New Body Region

1. **Update `region_map.json`:**
```json
"new_region_id": {
  "label": "Clinical Anatomy Label",
  "compendium_terms": ["term1", "term2", ...]
}
```

2. **Update SVG files:**
- Add clickable region to `assets/body_front.svg` and/or `assets/body_back.svg`
- Use correct `id` and `class="clickable-region"`

3. **Update UI grouping:**
- Edit `streamlit_app.py` region_groups dictionary

4. **Test:**
- Verify region is clickable
- Confirm search works
- Check term matching

5. **Document:**
- Update `REGION_REFERENCE.md`

### Improving Search Algorithm

Current algorithm in `streamlit_app.py`:

```python
combined_scores = 0.7 * embedding_sims + 0.3 * region_scores
```

To modify:
1. Edit the `search_cases()` function
2. Test with various queries
3. Document changes
4. Provide before/after comparisons

### Adding New Compendium Terms

Edit `region_map.json` to add synonyms:

```json
"cervical_spine": {
  "label": "Cervical Spine (C1-C7)",
  "compendium_terms": [
    "neck",
    "whiplash",
    // Add new terms here
    "cervical radiculopathy",
    "facet syndrome"
  ]
}
```

## Code Review Guidelines

When reviewing PRs, check:

### Functionality
- [ ] Feature works as intended
- [ ] No regressions
- [ ] Edge cases handled

### Code Quality
- [ ] Readable and maintainable
- [ ] Appropriate comments
- [ ] No code duplication
- [ ] Error handling present

### Testing
- [ ] Manual testing done
- [ ] Test coverage adequate
- [ ] No console errors

### Documentation
- [ ] README updated if needed
- [ ] Code comments clear
- [ ] API docs updated

## Git Commit Messages

Follow this format:

```
type: Brief description (max 50 chars)

Detailed explanation if needed (wrap at 72 chars)

- Bullet points for multiple changes
- Reference issues: Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, etc.)
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat: Add thoracic spine region to body map

Added thoracic spine as a distinct clickable region in the back view
SVG. Updated region_map.json with appropriate compendium terms.

Fixes #45
```

```
fix: Correct damage extraction regex

Previous regex missed cases where commas were omitted. Updated to
handle both $50000 and $50,000 formats.
```

## Community Guidelines

### Be Respectful
- Assume good intentions
- Provide constructive feedback
- Help others learn
- Be patient with newcomers

### Be Professional
- This tool is for legal professionals
- Maintain high quality standards
- Test thoroughly
- Document clearly

### Be Collaborative
- Share knowledge
- Review others' PRs
- Discuss approaches
- Build consensus

## Questions?

- Open a [Discussion](https://github.com/hordruma/ON_damages_compendium/discussions)
- Check existing issues
- Review documentation
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Recognition

Contributors will be:
- Listed in README.md
- Mentioned in release notes
- Credited in the app footer (for major contributions)

Thank you for helping improve access to legal precedent data!
