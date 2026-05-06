---
name: dd-framework
description: This skill enables AI agents to understand, use, and modify pages using the ldnddev Framework's component system. AI agents can add, configure, or update any framework component with proper parameters and best practices.
license: MIT
metadata:
    author: Jared Lyvers (ldnddev.com)
    version: 1.0.0
---

# Framework Component Skill - AI Agent Guidelines for ldnddev Framework

## Purpose
This skill enables AI agents to understand, use, and modify pages using the ldnddev Framework's component system. AI agents can add, configure, or update any framework component with proper parameters and best practices.

## Component Usage Pattern
AI agents can add components to pages using this structured approach:

```
[Component Name] + [Required Parameters] + [Optional Parameters] + [Placement Context]
```

## Available Components & Parameters

### Hero Component (`dd-hero`)
**File**: `/web/templates/components/dd-hero.html`
**Usage Context**: Full-width hero sections (does NOT require dd-section wrapper)

**Required Parameters**:
- `image`: Hero background image URL
- `title`: Main heading text
- `subtitle`: Supporting heading text

**Optional Parameters**:
- `copy`: Body text content
- `cta_text`: Call-to-action button text
- `cta_link`: Call-to-action button URL
- `cta_target`: Button target (`_self`, `_blank`, `_parent`)
- `image_alt`: Image alt text
- `image_mobile`: Mobile-optimized image URL
- `image_tablet`: Tablet-optimized image URL
- `image_desktop`: Desktop-optimized image URL

**Usage Examples**:
```html
<!-- Basic Hero -->
<section class="dd-hero" aria-label="Hero section">
  <div class="dd-hero__image">
    <picture>
      <img src="[image]" alt="[image_alt]" class="dd-img" />
    </picture>
  </div>
  <div class="dd-hero__content dd-g" data-aos="fade-in">
    <div class="dd-hero__copy dd-u-1-1 dd-u-lg-12-24">
      <div class="dd-hero__title"><h1>[title]</h1></div>
      <div class="dd-hero__subtitle"><strong>[subtitle]</strong></div>
      <div class="dd-hero__body"><p>[copy]</p></div>
      [if cta_text]<div class="dd-hero__cta">
        <a href="[cta_link]" target="[cta_target]" class="dd-button -primary">[cta_text]</a>
      </div>[/if]
    </div>
  </div>
</section>
```

### Card Component (`dd-card`)
**File**: `/web/templates/components/dd-card.html`
**Usage Context**: Grid/card layouts (requires dd-section wrapper)

**Required Parameters**:
- `title`: card title text
- `image`: card image URL

**Optional Parameters**:
- `subtitle`: card subtitle text
- `copy`: card body text
- `cta_text`: call-to-action button text
- `cta_link`: call-to-action button URL
- `image_alt`: image alt text
- `columns`: number of columns (2, 3, 4)
- `animate`: animation type (`fade-up`, `fade-in`, `slide-up`)

**Usage Examples**:
```html
<!-- Single Card -->
<div class="dd-card">
  <div class="dd-card__items dd-g">
    <div class="dd-card__item l-box dd-u-1-1 dd-u-md-12-24" data-aos="[animate]">
      <div class="dd-card__body dd-g">
        <div class="dd-card__image">
          <img src="[image]" alt="[image_alt]" class="dd-image" loading="lazy">
        </div>
        <div class="dd-card__copy l-box">
          <div class="dd-card__title"><h3>[title]</h3></div>
          [if subtitle]<div class="dd-card__sub-title"><strong>[subtitle]</strong></div>[/if]
          [if copy]<p>[copy]</p>[/if]
          [if cta_text]<div class="dd-card__links">
            <a href="[cta_link]" class="dd-button -primary">[cta_text]</a>
          </div>[/if]
        </div>
      </div>
    </div>
  </div>
</div>
```

### Section Component (`dd-section`)
**File**: `/web/templates/components/dd-section.html`
**Usage Context**: Wrapper for most components, provides consistent spacing and layout

**Required Parameters**:
- `content`: component content to wrap

**Optional Parameters**:
- `background`: background color (`primary`, `secondary`, `tertiary`, `gray`, `white`, `black`)
- `spacing`: vertical spacing (`tight`, `normal`, `loose`, `extra-loose`)
- `width`: content width (`narrow`, `normal`, `wide`, `full`)
- `align`: text alignment (`left`, `center`, `right`)

**Usage Examples**:
```html
<!-- Section wrapper -->
<section class="dd-section [background]" aria-label="Content section">
  <div class="dd-section__container dd-g">
    <div class="dd-section__item dd-u-1-1 [align] [width]">
      [content]
    </div>
  </div>
</section>
```

### Alert Component (`dd-alert`)
**File**: `/web/templates/components/dd-alert.html`
**Usage Context**: Success/error/info/warning messages (requires dd-section wrapper)

**Required Parameters**:
- `type`: alert type (`success`, `error`, `warning`, `info`)
- `message`: alert message text

**Optional Parameters**:
- `title`: alert title
- `dismissible`: add close button (`true/false`)

### Banner Component (`dd-banner`)
**File**: `/web/templates/components/dd-banner.html`
**Usage Context**: Promotional or announcement banners

**Required Parameters**:
- `message`: banner text
- `background`: banner background color

**Optional Parameters**:
- `link_text`: action link text
- `link_url`: action link URL
- `dismissible`: add close button

### Tabs Component (`dd-tabs`)
**File**: `/web/templates/components/dd-tabs.html`
**Usage Context**: Tabbed content sections

**Required Parameters**:
- `tabs`: array of tab objects with `title` and `content`

**Optional Parameters**:
- `default_tab`: which tab to show initially (0-indexed)
- `orientation`: tab orientation (`horizontal`, `vertical`)

### Accordion Component (`dd-accordion`)
**File**: `/web/templates/components/dd-accordion.html`
**Usage Context**: Expandable/collapsible content sections

**Required Parameters**:
- `items`: array of accordion items with `title` and `content`

**Optional Parameters**:
- `multiple`: allow multiple open items (`true/false`)

### CTA Component (`dd-cta`)
**File**: `/web/templates/components/dd-cta.html`
**Usage Context**: Call-to-action sections

**Required Parameters**:
- `title`: CTA heading
- `copy`: CTA description
- `cta_text`: button text
- `cta_link`: button URL

### Modal Component (`dd-modal`)
**File**: `/web/templates/components/dd-modal.html`
**Usage Context**: Popup/overlaid content

**Required Parameters**:
- `trigger_text`: button/link to open modal
- `title`: modal title
- `content`: modal content

### Slider Component (`dd-slider`)
**File**: `/web/templates/components/dd-slider.html`
**Usage Context**: Carousel/sliding content

**Required Parameters**:
- `slides`: array of slide objects with `image`, `title`, `copy`

**Optional Parameters**:
- `autoplay`: auto-advance slides (`true/false`)
- `speed`: transition speed (ms)

### Spacer Component (`dd-spacer`)
**File**: `/web/templates/components/dd-spacer.html`
**Usage Context**: Vertical spacing control

**Required Parameters**:
- `height`: spacing size (`sm`, `md`, `lg`, `xl`, `xxl`,)

### Timeline Component (`dd-timeline`)
**File**: `/web/templates/components/dd-timeline.html`
**Usage Context**: Chronological event displays

**Required Parameters**:
- `events`: array of timeline events with `date`, `title`, `description`

## Color System & WCAG Compliance

Reference `Agent-UI-Colors.md` and `Agent-UI-Theme-Builder.md` for color specifications:

- **Primary**: `#88d9f7` (rgba(136, 217, 247, 1))
- **Secondary**: `#ffca76` (rgba(255, 202, 118, 1))
- **Tertiary**: `#f98971` (rgba(249, 137, 113, 1))
- **Support**: `#46be8c` (rgba(70, 190, 140, 1))

**Text Colors**:
- Light mode: `#1c1e21` (primary text), `#5a5f66` (secondary text)
- Dark mode: `#f5f6f7` (primary text), `#9ea3aa` (secondary text)

### WCAG Compliance Guidelines
- All interactive components must meet AA contrast (4.5:1 for normal text, 3:1 for large text)
- Ensure focus indicators are visible (2px solid outline minimum)
- Provide alt text for all images
- Use semantic HTML elements for proper screen reader support

## Development Workflow

### Building Changes
All commands must be run with `lando` prefix:
```bash
lando grunt build        # Full build
lando grunt dev          # Development build with watching
lando grunt sync         # Sync assets to web directory
```

### Adding Components to Pages
1. **Identify placement**: Determine where in the page the component should appear
2. **Check context**: Verify if component requires dd-section wrapper (hero does not)
3. **Use templates**: Copy from `/web/templates/components/` as starting point
4. **Update parameters**: Replace placeholder values with actual content
5. **Test responsive**: Verify mobile, tablet, desktop views
6. **Test accessibility**: Validate with screen readers and keyboard navigation

### Code Standards
```html
<!-- Preferred structure -->
<section class="dd-section" aria-label="[descriptive label]">
  <div class="dd-section__container dd-g">
    <div class="dd-section__item dd-u-1-1">
      [component content]
    </div>
  </div>
</section>

<!-- Use semantic elements -->
<article>, <section>, <header>, <footer>, <nav>, <aside>

<!-- Provide descriptive text for screen readers -->
aria-label, aria-describedby, aria-labelledby

<!-- Add animation classes -->
data-aos="fade-up", data-aos="fade-in", data-aos="slide-up"
```

## Performance Optimization

- **Image optimization**: Use responsive images with srcset
- **Lazy loading**: Add `loading="lazy"` to images
- **Minification**: All CSS/JS is automatically minified
- **CDN integration**: Assets can be served from CDN in production

## Common Patterns & Templates

### Full Page Template
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Page Title]</title>
    <link rel="stylesheet" href="/assets/css/style.min.css">
    <meta name="description" content="[Page description]">
</head>
<body class="dd-g">
    <!-- Header -->
    <header class="dd-header">
        <!-- Content -->
    </header>

    <!-- Main Content -->
    <main>
        <!-- Hero (doesn't need dd-section) -->
        [hero component]
        
        <!-- Other content (needs dd-section) -->
        <section class="dd-section" aria-label="[section label]">
        <div class="dd-section__container dd-g">
          <div class="dd-section__item dd-u-1-1">
            [other components]
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="dd-footer">
        <!-- Content -->
    </footer>

    <script src="/assets/js/main.min.js"></script>
</body>
</html>
```

### Component Integration Commands
When asked to add/modify components, use these patterns:

**Add hero to page**: "Add a dd-hero component with [image] as background, title '[title]', subtitle '[subtitle]', copy '[copy]', and CTA button '[cta_text]' linking to [cta_link]"

**Add card grid**: "Add a dd-card component with 3 cards arranged in a grid, each has image, title, subtitle, and CTA"

**Add alert**: "Add a dd-alert component at the top of the page with type 'success' and message '[message]'"

**Update content**: "Replace the hero title on [page] with '[new title]'"

### Responsive Classes Reference
- **Grid**: `dd-u-1-1`, `dd-u-md-12-24`, `dd-u-lg-8-24`, `dd-u-xl-6-24`
- **Spacing**: `l-box` (container), `m-bottom`, `m-top`, `p-large`, `p-small`
- **Alignment**: `dd-t-center`, `dd-t-left`, `dd-t-right`
- **Visibility**: `dd-d-none`, `dd-d-block`, `dd-d-md-block`

## Troubleshooting

### Common Issues
1. **Styles not loading**: Check file paths, run `lando grunt build`
2. **Components not displaying**: Ensure proper dd-section wrapper
3. **Images not responsive**: Add proper srcset attributes
4. **Animations not triggering**: Ensure AOS library is loaded
5. **Contrast issues**: Check color combinations against WCAG guidelines

### Debug Commands
```bash
lando grunt build --verbose    # Detailed build information
lando grunt watch              # Auto-rebuild on changes
lando lando info               # Environment information
