/** Short aliases for the generated schema types used across the app. */
import type { components } from './schema';

type S = components['schemas'];

export type SessionInfo = S['SessionInfo'];
export type SessionUser = S['SessionUser'];
export type MenuResponse = S['MenuResponse'];
export type MenuCard = S['MenuCard'];
export type MenuSauce = S['MenuSauce'];
export type VariantOptions = S['VariantOptions'];
export type VariantOption = S['VariantOption'];
export type AddToCartRequest = S['AddToCartRequest'];
export type CartView = S['CartView'];
export type CartLine = S['CartLine'];
export type CartPreview = S['CartPreview'];
export type CartItemDetail = S['CartItemDetail'];
export type CheckoutView = S['CheckoutView'];
export type CheckoutRequest = S['CheckoutRequest'];
export type HomePage = S['HomePage'];
export type HomeProduct = S['HomeProduct'];
export type ReviewsPage = S['ReviewsPage'];
export type GalleryPage = S['GalleryPage'];
export type ProfileView = S['ProfileView'];
export type ProfileOrder = S['ProfileOrder'];
export type AboutBlock = S['AboutBlock'];
export type UpdateCartItemRequest = S['UpdateCartItemRequest'];
