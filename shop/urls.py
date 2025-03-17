from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    
    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add-to-cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update-cart-item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove-from-cart'),
    path('cart/checkout/', views.checkout, name='checkout'),
    
    # Customer Orders
    path('my/orders/', views.OrderListView.as_view(), name='order-list'),
    path('my/orders/<uuid:order_id>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('my/orders/<uuid:order_id>/cancel/', views.cancel_order, name='cancel-order'),
    
    # Farmer Orders
    path('farmer/orders/', views.FarmerOrderListView.as_view(), name='farmer-orders'),
    path('farmer/orders/<uuid:order_id>/', views.FarmerOrderDetailView.as_view(), name='farmer-order-detail'),
    path('farmer/orders/<uuid:order_id>/status/', views.update_order_status, name='update-order-status'),
    path('farmer/orders/<uuid:order_id>/cancel/', views.cancel_order, name='cancel-order'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
