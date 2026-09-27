# Coffee Time: Jinja SSR → JSON API + React SPA

Working plan for the rewrite. The PR description records the final decisions and trade-offs.

## Target layout

```
app/                    FastAPI, now JSON only (everything under /api)
  api/                  shared API plumbing: error envelope, CSRF dependency, router assembly
  schemas/              Pydantic request/response models, the source of /openapi.json
  routers/public/*.py   same files, same services, JSON responses instead of templates
  routers/admin/*.py    same
  services/*.py         business logic, mostly untouched (see "Behaviour fixes")
static/                 still served by FastAPI at /static (product photos, admin uploads)
frontend/               new React SPA
  src/api/              openapi-fetch client, generated schema.d.ts, CSRF handling
  src/features/<area>/  pages, components and hooks for one area (menu, cart, checkout, …)
  src/admin/            admin panel (lazy-loaded chunk)
  src/components/       shared layout pieces (Header, Footer, Modal, Toast, …)
  src/styles/           the existing CSS, reused as global stylesheets
render.yaml             backend web service + new static site with /api and /static rewrites
```

## API conventions

- Every endpoint lives under `/api`, with Pydantic `response_model`s, so
  `openapi-typescript` generates exact types.
- Errors use one envelope, `{detail, code?, errors?[]}`, with a proper status
  code (400 validation, 401 not logged in, 403 CSRF/permission, 404).
- Sessions: the same DB-backed cookie session. The SPA calls with
  `credentials: 'include'` from the same origin, via a Vite proxy in dev and
  Render rewrites in production.
- CSRF: `GET /api/csrf-token`. The client sends it back in `X-CSRF-Token` on
  every POST/PUT/PATCH/DELETE. The server check is still `hmac.compare_digest`
  against the session token, and it applies to the whole `/api` router. The only
  exemptions are the two LiqPay endpoints that LiqPay itself calls.
- Uploads stay `multipart/form-data`, with explicit `Form`/`UploadFile` params
  so they show up in the schema.

## Stages (one or more commits each)

1. API plumbing: error envelope, header CSRF, `/api/session`, `/api/csrf-token`.
2. Public API: home, menu, cart, checkout, LiqPay/payments, auth, profile,
   reviews, gallery, pages. Tests rewritten against JSON.
3. Admin API: dashboard, orders, products, sauces, gallery, reviews, hero
   slides, about, dessert banner, staff, backup. Tests rewritten.
4. Delete Jinja: templates, `templating.py`, the old JS, the jinja2 dependency.
5. Frontend scaffold: Vite + React 19 + TS, Router, TanStack Query,
   openapi-fetch, type generation script, Vitest.
6. Storefront pages: layout (header with cart mini-dropdown, footer), home,
   menu (tabs, search, filters, item modal, sauce picker), cart (inline edit),
   checkout (drum time picker), LiqPay auto-submit, payment result pages
   (pending polls status).
7. Account pages: login/register/forgot/reset/change-password, profile,
   reviews, gallery (CSS-columns masonry), about/contact.
8. Admin SPA: layout/sidebar with perms, dashboard (Chart.js), orders,
   products CRUD with image crop, sauces, gallery, reviews, hero slides,
   about, dessert banner, staff, backup.
9. Vitest coverage for cart/menu/checkout logic and key forms.
10. Deploy config (render.yaml static site + rewrites), README, PR.

## Behaviour fixes to make along the way

- **Prices are computed only on the server.** `price_override` from the client
  is ignored everywhere. Variant surcharges (ice-cream scoops, fast-food
  size/filling) are looked up in the product's `variant_options` by option id,
  never read from the client JSON's `price_diff`. Line prices are re-derived
  from the DB at checkout.
- A large pizza added without a client price was charged the small price. It
  now always uses `price_large`.
- Ice cream and sauces were shown in the cart but silently dropped from the
  order at checkout. They are now part of the order.
- The admin orders "type" filter looked at `delivery_address`, which is always
  empty. It now uses `order_type`.
