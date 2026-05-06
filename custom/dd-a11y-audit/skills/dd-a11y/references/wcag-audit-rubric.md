# WCAG Audit Rubric
<!-- Updated: 2026-04-19 -->

## Mandatory Evidence Format

All accessibility findings MUST include:

### 1. Finding Structure
```markdown
**Finding:** [Clear description of the accessibility issue]
**Element:** [CSS selector, XPath, or element description]
**Evidence:** [Code snippet, screenshot reference, or tool output]
**WCAG Reference:** [WCAG 2.2 Success Criterion, e.g., "1.4.3 Contrast (Minimum)"]
**Impact:** [Which user groups are affected: visual, motor, cognitive, auditory]
**Severity:** [Critical, Serious, Moderate, Minor]
**Confidence:** [Confirmed, Likely, Hypothesis]
**Fix:** [Clear implementation steps with code example]
```

### 2. Severity Levels

| Level | Criteria | Color | Priority |
|-------|----------|-------|----------|
| **🔴 Critical** | Blocks core functionality, violates WCAG Level A, affects all users | Red | Fix immediately |
| **⚠️ Serious** | Significant barrier, violates WCAG Level AA, affects many users | Orange | Fix within 7 days |
| **🟡 Moderate** | Usability issue, violates best practices, affects some users | Yellow | Fix within 30 days |
| **🟢 Minor** | Enhancement opportunity, minor usability impact | Green | Fix when convenient |
| **✅ Pass** | Meets or exceeds WCAG requirements | Blue | No action needed |
| **ℹ️ Info** | Not applicable or informational only | Gray | For reference only |

### 3. Confidence Levels

| Level | Meaning | When to Use |
|-------|---------|-------------|
| **Confirmed** | Direct observation, automated tool verification, manual testing | When issue is reproducibly verified |
| **Likely** | Strong evidence, pattern matching, expert judgment | When evidence strongly suggests issue exists |
| **Hypothesis** | Educated guess based on common patterns | When limited testing available, needs verification |

## Scoring Framework

### Category Weights (Default)

| Category | Weight | Description |
|----------|--------|-------------|
| **Perceivable** | 25% | Text alternatives, sensory characteristics, distinguishable content |
| **Operable** | 25% | Keyboard access, enough time, seizures, navigable, input modalities |
| **Understandable** | 25% | Readable, predictable, input assistance |
| **Robust** | 25% | Compatible with assistive technologies |

### Scoring Formula
```
Category Score = (Passing Criteria / Total Criteria) × 100
Overall Score = Σ(Category Score × Category Weight)
```

### Score Interpretation

| Score Range | Rating | Compliance Level | Action Required |
|-------------|--------|-----------------|-----------------|
| **90-100** | AA Compliant | WCAG 2.2 Level AA | Maintenance only |
| **75-89** | A Compliant | WCAG 2.2 Level A | Address AA issues |
| **50-74** | Needs Improvement | Partial compliance | Priority remediation |
| **25-49** | Significant Barriers | Major non-compliance | Urgent remediation |
| **0-24** | Critical Barriers | Severe non-compliance | Complete overhaul |

## Evidence Requirements

### Automated Tool Evidence
- **axe-core**: Include violation ID, impact, nodes affected
- **pa11y**: Include standard, code snippet, context
- **Lighthouse**: Include audit ID, score, opportunities

### Manual Testing Evidence
- **Keyboard**: Document tab order, focus indicators, keyboard traps
- **Screen Reader**: Document NVDA/VoiceOver/JAWS output
- **Color Contrast**: Include color codes, contrast ratio, failing elements
- **Mobile**: Document viewport, touch targets, gestures

### Visual Evidence
- **Screenshots**: Annotated with issue location
- **Code Snippets**: Highlight problematic code
- **Before/After**: When demonstrating fixes

## Report Structure

### 1. Executive Summary
- Overall score and rating
- Critical issues summary
- Compliance status (A/AA/AAA)
- Mobile accessibility assessment

### 2. Detailed Findings
Grouped by WCAG principle with:
- Summary table (Element, Issue, WCAG Reference, Severity, Status)
- Detailed findings with evidence
- Screenshots and code examples

### 3. Compliance Matrix
- WCAG 2.2 success criteria checklist
- Pass/Fail/Not Applicable status
- Mobile-specific compliance

### 4. Remediation Plan
- Prioritized action items
- Implementation timeline (Immediate, 7 days, 30 days, 90 days)
- Resource requirements
- Testing validation steps

### 5. Legal Compliance
- ADA compliance status
- Section 508 compliance
- Other relevant regulations

## Quality Gates

### Pre-Report Validation
1. **Evidence Completeness**: All findings must have supporting evidence
2. **Severity Justification**: Each severity level must be justified
3. **WCAG Mapping**: Each issue must map to specific success criteria
4. **Fix Feasibility**: All fixes must be technically feasible

### Post-Report Requirements
1. **Google Drive Report**: Upload to "Audits" folder
2. **Artifact List**: Explicit list of generated files
3. **Path References**: Clear paths to all generated artifacts
4. **Environment Notes**: Document any testing limitations

## Testing Limitations Handling

### When Automated Tools Fail
- Report as "Environment Limitation"
- Set confidence to "Hypothesis"
- Continue with manual analysis
- Document missing data source

### When Manual Testing Limited
- Acknowledge partial coverage
- Focus on high-impact areas
- Recommend follow-up testing
- Provide testing checklist

### Network/DNS Issues
- One retry maximum
- Report as "Testing Blocked"
- Provide offline checklist
- Recommend local testing

## Mobile Accessibility Specifics

### Testing Requirements
- **Viewports**: 320px, 375px, 414px (mobile), 768px (tablet)
- **Touch Targets**: Minimum 44×44 CSS pixels
- **Gestures**: Test with single pointer alternatives
- **Orientation**: Test portrait and landscape

### Mobile-Specific Issues
- **Touch Target Size**: Below 44×44 pixels
- **Gesture Complexity**: Requires multi-finger gestures
- **Viewport Issues**: Content doesn't reflow
- **Zoom Restrictions**: Content not zoomable

## Legal Compliance Notes

### ADA Requirements
- WCAG 2.0/2.1 Level AA minimum
- Public accommodations and commercial facilities
- Website accessibility statement required

### Section 508
- WCAG 2.0 Level AA
- Federal agencies and contractors
- VPAT (Voluntary Product Accessibility Template) may be required

### International Standards
- **EN 301 549**: EU public sector (WCAG 2.1 AA)
- **AODA**: Ontario, Canada (WCAG 2.0 AA)
- **JIS X 8341-3**: Japan (based on WCAG 2.0)

## Continuous Improvement

### Signal Freshness
- Reference files updated quarterly
- WCAG updates tracked within 30 days
- Tool versions documented
- Testing methodologies reviewed annually

### Feedback Integration
- User testing results incorporated
- Automated tool improvements tracked
- Manual testing protocols updated
- Report templates refined based on client feedback