"""Request/response models for /api/admin/*."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import Schema

# ── Layout ──

class AdminPerms(Schema):
    orders_view: bool
    orders_edit: bool
    products: bool
    content: bool
    reviews: bool


class NotifOrder(Schema):
    order_id: int
    name: str
    total: float
    time_label: str


class AdminLayout(Schema):
    username: str
    initial: str
    display_name: str
    role: Literal["super", "staff"]
    is_super: bool
    perms: AdminPerms
    can_see_orders: bool
    new_orders_count: int
    notif_orders: list[NotifOrder]
    pending_reviews: int


# ── Dashboard ──

class StatCompare(Schema):
    direction: Literal["up", "down", "eq"]
    text: str


class AdminPayBadge(Schema):
    cls: str
    icon: str
    label: str


class RecentOrder(Schema):
    order_id: int
    full_name: str
    phone: str
    total: float
    status: str
    status_label: str
    status_class: str
    pay_badge: AdminPayBadge
    created_at: str


class TopProduct(Schema):
    name: str
    image: str
    deleted: bool
    sold: int
    orders_count: int
    total_revenue: float
    unit_price: str


class CategoryCount(Schema):
    key: str
    label: str
    count: int


class StaffStats(Schema):
    """Only the blocks the admin has permissions for are filled in."""
    products_total: int | None = None
    sauces_total: int | None = None
    reviews_total: int | None = None
    reviews_week: int | None = None
    gallery_total: int | None = None
    gallery_food: int | None = None
    gallery_interior: int | None = None
    slides_total: int | None = None
    slides_active: int | None = None
    about_title: str | None = None
    about_text: str | None = None
    about_photo: str | None = None


class DashboardCompare(Schema):
    orders: StatCompare
    revenue: StatCompare
    avg_check: StatCompare
    clients: StatCompare
    reviews: StatCompare


class FullDashboard(Schema):
    today_orders: int
    today_revenue: float
    avg_check: int
    total_clients: int
    week_reviews: int
    compare: DashboardCompare
    show_reviews_stat: bool
    hours_data: list[int]
    week_data: list[int]
    week_labels: list[str]
    month_data: list[int]
    month_labels: list[str]
    recent_orders: list[RecentOrder]
    top_products: list[TopProduct]
    today_iso: str


class DashboardResponse(Schema):
    # "staff": a staff member without orders access gets a welcome page
    # with their own sections' stats instead of the sales dashboard.
    mode: Literal["staff", "full"]
    staff_stats: StaffStats
    categories: list[CategoryCount]
    full: FullDashboard | None = None
    weekday: str
    today_str: str
    role_label: str


class CountResponse(Schema):
    count: int


class ChartData(Schema):
    success: bool
    data: list[int] = []


class TopProductsResponse(Schema):
    success: bool
    products: list[TopProduct]


class OrderCounts(Schema):
    all: int
    new: int
    processing: int = 0
    ready: int = 0
    done: int
    cancelled: int
    paid: int
    cash: int
    unpaid: int


# ── Orders ──

class AdminOrderItem(Schema):
    product_name: str
    product_image: str
    category: str
    quantity: int
    price: float
    opts: list[str]


class AdminOrderRow(Schema):
    order_id: int
    items_count: int
    full_name: str
    phone: str
    total: float
    status: str
    payment_status: str
    payment_method: str
    order_type: str
    ready_time: str
    comment: str
    created_at: str
    pay_badge: AdminPayBadge
    next_allowed: list[str]
    line_items: list[AdminOrderItem]


class AdminOrdersPage(Schema):
    orders: list[AdminOrderRow]
    total: int
    page: int
    total_pages: int
    counts: OrderCounts
    status_labels: dict[str, str]
    next_labels: dict[str, str]


class AdminOrderDetail(AdminOrderRow):
    customer_email: str
    client_name: str
    client_email: str | None
    paid_at: str | None
    payment_method_label: str
    rating: int | None


class StatusChangeRequest(Schema):
    status: str


class StatusChangeResult(Schema):
    success: bool
    error: str | None = None
    label: str | None = None
    new_status: str | None = None
    next_allowed: list[str] = []
    new_count: int = 0


class BulkStatusRequest(Schema):
    order_ids: list[int]
    status: str


class BulkStatusResult(Schema):
    success: bool
    error: str | None = None
    updated: int = 0
    skipped: int = 0
    new_count: int = 0
    label: str | None = None


# ── Products ──

class AdminProduct(Schema):
    id: int
    category: str
    category_label: str
    name: str
    description: str
    price: float
    image: str
    has_photo: bool
    sold: int = 0
    variant_options: str | None = None
    pieces_count: int | None = None
    price_per_kg: float | None = None
    min_weight: float | None = None
    scoop_diff_2: float | None = None
    scoop_diff_3: float | None = None


class AdminProductsPage(Schema):
    is_all: bool
    category: str
    title: str
    categories: list[CategoryCount]
    total_count: int
    products: list[AdminProduct]


class ProductSaved(Schema):
    product: AdminProduct


# ── Sauces ──

class AdminSauce(Schema):
    id: int
    name: str
    price: float
    image: str
    has_photo: bool
    active: bool
    sort_order: int


class SauceActiveRequest(Schema):
    active: bool


class SauceSaved(Schema):
    success: bool = True
    sauce: AdminSauce


# ── Gallery ──

class AdminGalleryImage(Schema):
    id: int
    url: str
    alt: str
    category: Literal["food", "interior"]
    created_at: str


class GalleryCounts(Schema):
    all: int
    food: int
    interior: int


class AdminGalleryPage(Schema):
    images: list[AdminGalleryImage]
    counts: GalleryCounts
    filter: str


class GalleryUploadResult(Schema):
    uploaded: int
    errors: list[str]


class GalleryPatch(Schema):
    category: Literal["food", "interior"] | None = None
    alt: str | None = None


# ── Reviews ──

class AdminReview(Schema):
    id: int
    author: str
    initial: str
    color: str
    rating: int
    text: str
    created_at: str
    status: Literal["approved", "declined", "pending"]


class RatingCount(Schema):
    stars: int
    count: int


class AdminReviewsPage(Schema):
    reviews: list[AdminReview]
    total_rows: int
    page: int
    total_pages: int
    filter_rating: int
    filter_status: str
    total_count: int
    avg_rating: float
    rating_dist: list[RatingCount]
    this_week: int


class AdminOrderRating(Schema):
    order_id: int
    uname: str
    email: str
    rating: int
    created_at: str


class AdminOrderRatingsPage(Schema):
    order_ratings: list[AdminOrderRating]
    total: int
    avg: float
    week: int
    page: int
    total_pages: int


class ReviewStatusRequest(Schema):
    status: Literal["approved", "declined", "pending"]


# ── Hero slides ──

class AdminHeroSlide(Schema):
    id: int
    image: str
    label: str
    title: str
    subtitle: str
    sort_order: int
    active: bool


class SlideMoveRequest(Schema):
    dir: Literal["up", "down"]


class SlideToggleResult(Schema):
    ok: bool = True
    active: bool


# ── About section / dessert banner ──

class AboutSettings(Schema):
    about_title: str
    about_text: str
    about_founded_year: str
    about_menu_count: str
    about_rating: str
    about_photo: str
    years_open: int


class DessertBannerSettings(Schema):
    dessert_banner_label: str
    dessert_banner_title: str
    dessert_banner_desc: str
    dessert_banner_btn: str
    image: str | None
    has_custom_image: bool
    # Without a custom photo the site shows a random dessert; one sample.
    random_image: str | None = None


# ── Staff ──

class PermOption(Schema):
    key: str
    label: str


class AdminAccount(Schema):
    id: int
    username: str
    display_name: str
    role: Literal["super", "staff"]
    perms: list[str]
    is_me: bool


class AdminUsersPage(Schema):
    users: list[AdminAccount]
    all_perms: list[PermOption]


class AdminUserCreate(Schema):
    username: str = ""
    display_name: str = ""
    password: str = ""
    perms: list[str] = Field(default_factory=list)


class AdminUserUpdate(Schema):
    display_name: str = ""
    perms: list[str] = Field(default_factory=list)
    new_password: str = ""


class MyAccountUpdate(Schema):
    display_name: str = ""
    current_password: str = ""
    new_password: str = ""


class MessageResult(Schema):
    ok: bool = True
    message: str
