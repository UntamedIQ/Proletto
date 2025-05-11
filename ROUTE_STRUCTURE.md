# Proletto Route Structure

## Access Levels

### Public Pages (No Login Required)
| URL | Purpose | Template | Status |
|-----|---------|----------|--------|
| `/` | Homepage | templates/public/index.html | Current: templates/index.html |
| `/how-it-works` | How-It-Works guide | templates/public/how_it_works.html | Current: templates/how_it_works.html |
| `/membership` | Pricing / sign-up funnel | templates/public/membership.html | Current: templates/membership.html |
| `/login`, `/register`, etc. | Auth flows | templates/public/auth/... | Current: templates/login.html, templates/register.html |
| `/healthz`, `/cache-health` | Health checks | N/A | Implemented |

### Member Pages (Login Required)
| URL | Purpose | Template | Status |
|-----|---------|----------|--------|
| `/dashboard` | Dashboard home | templates/member/dashboard.html | Current: templates/dashboard.html |
| `/dashboard/feed` | New feed interface—TikTok-style infinite scroll | templates/member/feed.html | To be implemented (replace /opportunities) |
| `/dashboard/curation` | Personalized "top 5" picks | templates/member/curation.html | To be implemented |
| `/dashboard/portfolio` | Gallery upload & management | templates/member/portfolio.html | Current: templates/portfolio.html |
| `/dashboard/portfolio-optimizer` | AI-powered portfolio analysis | templates/member/portfolio_optimizer.html | Current: templates/portfolio_optimizer.html |
| `/dashboard/settings` | Alerts, digests, preferences | templates/member/settings.html | To be implemented |
| `/dashboard/submit` | Gallery / Event submissions | templates/member/submit.html | To be implemented |

### Admin Pages (Admin Only)
| URL | Purpose | Template | Status |
|-----|---------|----------|--------|
| `/admin/dragon-status` | Dragon scheduler & system health dashboard | templates/admin/dragon_status.html | Implemented |
| `/admin/cache-utils/health` | Cache health & manual resets | N/A | Implemented |
| `/admin/rescue/*` | Emergency cache/scheduler rescue endpoints | N/A | To be implemented |

## Implementation Plan

### 1. Update Navigation
- Public layout: link only to public routes (Home, How-It-Works, Pricing, Login)
- Member layout: include the full /dashboard/* menu (Feed, Portfolio, Optimizer, Submissions, Settings)

### 2. Deprecate Old Routes
- Redirect `/opportunities` to `/dashboard/feed`
- Redirect `/portfolio` to `/dashboard/portfolio`
- Redirect `/portfolio-optimizer` to `/dashboard/portfolio-optimizer`

### 3. Ensure Access Control
- Verify every `/dashboard/*` route is decorated with `@login_required`
- Protect `/admin/*` with an `@admin_required` decorator

### 4. Consolidate Templates
- Move all public templates under `templates/public/`
- All member views under `templates/member/`
- Admin under `templates/admin/`

### 5. Document the Route Map
- Keep this document updated as the source of truth for route organization