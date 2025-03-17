from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count, F, Sum, Avg
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from decimal import Decimal

from .forms import (
    UserRegistrationForm, ProductForm, CartItemForm,
    ShippingAddressForm, OrderForm
)
from .models import (
    Product, Category, Cart, CartItem,
    Order, OrderItem
)

class FarmerRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict view access to farmers only"""
    
    def test_func(self):
        return self.request.user.is_farmer
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Only farmers can access this page.")
        return super().handle_no_permission()

def home(request):
    return render(request, 'shop/home.html')

class SignUpView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'shop/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        login(self.request, user)
        return redirect('home')

class CustomLoginView(LoginView):
    template_name = 'shop/login.html'
    redirect_authenticated_user = True
    next_page = 'home'

class CustomLogoutView(LogoutView):
    next_page = 'home'
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

class ProductListView(ListView):
    model = Product
    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_available=True)
        
        # Filter by farmer if user is a farmer
        if self.request.user.is_authenticated and self.request.user.is_farmer:
            queryset = queryset.filter(farmer=self.request.user)
        
        # Filter by category if specified
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter by search query if specified
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        return queryset.select_related('category', 'farmer')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('q')
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'shop/product_detail.html'  # Path to your template
    context_object_name = 'product'  # Name of the context variable in the template

    def get_object(self, queryset=None):
        # Fetch the product using the primary key (pk) from the URL
        pk = self.kwargs.get('pk')
        return get_object_or_404(Product.objects.select_related('category', 'farmer').prefetch_related('offers'), pk=pk)

    def get_context_data(self, **kwargs):
        # Add additional context data to the template
        context = super().get_context_data(**kwargs)
        
        # Add related products (e.g., products from the same category)
        product = self.get_object()
        related_products = Product.objects.filter(category=product.category).exclude(pk=product.pk)[:4]
        
        context['related_products'] = related_products
        context['categories'] = Category.objects.all()  # Add all categories for navigation
        return context

class ProductCreateView(LoginRequiredMixin, FarmerRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'shop/product_form.html'
    success_url = reverse_lazy('product-list')

    def form_valid(self, form):
        form.instance.farmer = self.request.user
        messages.success(self.request, 'Product created successfully!')
        return super().form_valid(form)

class ProductUpdateView(LoginRequiredMixin, FarmerRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'shop/product_form.html'
    success_url = reverse_lazy('product-list')

    def get_queryset(self):
        # Ensure farmers can only edit their own products
        return Product.objects.filter(farmer=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Product updated successfully!')
        return super().form_valid(form)

class ProductDeleteView(LoginRequiredMixin, FarmerRequiredMixin, DeleteView):
    model = Product
    template_name = 'shop/product_confirm_delete.html'
    success_url = reverse_lazy('product-list')

    def get_queryset(self):
        # Ensure farmers can only delete their own products
        return Product.objects.filter(farmer=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Product deleted successfully!')
        return super().delete(request, *args, **kwargs)

class CategoryListView(ListView):
    model = Category
    template_name = 'shop/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.annotate(
            product_count=Count('products')
        ).order_by('name')

@login_required
def cart_view(request):
    """View shopping cart contents"""
    try:
        # Get or create cart with prefetched items
        cart = Cart.objects.prefetch_related(
            'items',
            'items__product',
            'items__product__category',
            'items__product__farmer'
        ).get_or_create(user=request.user)[0]
        
        # Validate cart items and remove invalid ones
        invalid_items = []
        for item in cart.items.all():
            try:
                item.clean()
            except ValidationError as e:
                invalid_items.append((item, str(e)))
                item.delete()
        
        if invalid_items:
            for item, error in invalid_items:
                messages.warning(
                    request,
                    f"Removed {item.product.name}: {error}"
                )
        
        # Group items by farmer
        items_by_farmer = {}
        for item in cart.items.all():
            farmer = item.product.farmer
            if farmer not in items_by_farmer:
                items_by_farmer[farmer] = {
                    'items': [],
                    'subtotal': Decimal('0.00')
                }
            items_by_farmer[farmer]['items'].append(item)
            if item.price_at_time and item.quantity:
                items_by_farmer[farmer]['subtotal'] += item.price_at_time * item.quantity
        
        # Calculate delivery fee
        delivery_fee = Decimal('50.00')  # Move to settings later
        
        context = {
            'cart': cart,
            'items_by_farmer': items_by_farmer,
            'delivery_fee': delivery_fee,
            'total': cart.total_price,
            'total_with_delivery': cart.total_with_delivery
        }
        
        return render(request, 'shop/cart.html', context)
        
    except Cart.DoesNotExist:
        messages.error(request, "Could not find your cart. Please try again.")
        return redirect('product-list')
    except Exception as e:
        messages.error(request, f"Error loading cart: {str(e)}")
        return redirect('product-list')

@login_required
def add_to_cart(request, product_id):
    """Add a product to cart"""
    try:
        product = get_object_or_404(Product, id=product_id, is_available=True)
        
        if request.method == 'POST':
            try:
                quantity = Decimal(request.POST.get('quantity', product.min_quantity))
                
                # Get or create cart
                cart, created = Cart.objects.get_or_create(user=request.user)
                
                # Check if mixing products from different farmers
                existing_item = cart.items.exclude(product=product).first()
                if existing_item and existing_item.product.farmer != product.farmer:
                    raise ValidationError("Cannot mix products from different farmers in the same cart")
                
                # Get or create cart item
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={
                        'quantity': quantity,
                        'price_at_time': product.base_price
                    }
                )
                
                if not created:
                    # Update quantity and refresh price
                    cart_item.quantity += quantity
                    cart_item.price_at_time = product.base_price
                
                # This will trigger validation in clean()
                cart_item.full_clean()
                cart_item.save()
                
                messages.success(request, f"Added {product.name} to cart")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': f"Added {product.name} to cart",
                        'cart_total': cart.total_price
                    })
                return redirect('cart')
                
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
            except ValueError:
                messages.error(request, "Invalid quantity specified")
            except Exception as e:
                messages.error(request, f"Error adding to cart: {str(e)}")
    
    except Product.DoesNotExist:
        messages.error(request, "Product not found or unavailable")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': messages.get_messages(request)[-1].message})
    return redirect('product-list')

@login_required
def update_cart_item(request, item_id):
    """Update quantity of a cart item"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = Decimal(request.POST.get('quantity', 0))
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, "Item removed from cart")
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'removed': True,
                'cart_total': float(cart_item.cart.total_price)
            })
        
        # Update quantity and refresh price
        cart_item.quantity = quantity
        cart_item.price_at_time = cart_item.product.base_price
        
        try:
            cart_item.full_clean()
            cart_item.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Cart updated',
                'item_total': float(cart_item.total_price),
                'cart_total': float(cart_item.cart.total_price)
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': '; '.join(e.messages)
            })
            
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart item not found'
        })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid quantity'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
def remove_from_cart(request, item_id):
    """Remove an item from cart"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
        
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart = cart_item.cart
        cart_item.delete()
        messages.success(request, "Item removed from cart")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'cart_total': float(cart.total_price)
            })
        return redirect('cart')
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
def checkout(request):
    """Process checkout and create order"""
    try:
        cart = Cart.objects.select_related('user').prefetch_related(
            'items',
            'items__product',
            'items__product__farmer'
        ).get(user=request.user)
        
        if not cart.items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect('cart')
        
        if request.method == 'POST':
            form = ShippingAddressForm(request.POST, user=request.user)
            if form.is_valid():
                try:
                    # Validate all items before starting transaction
                    for item in cart.items.all():
                        if not item.product.is_available:
                            raise ValidationError(f"{item.product.name} is no longer available")
                        if item.quantity > item.product.stock_quantity:
                            raise ValidationError(
                                f"Only {item.product.stock_display} available for {item.product.name}"
                            )
                        item.full_clean()
                    
                    # Start atomic transaction after validation
                    with transaction.atomic():
                        # Create order
                        order = Order.objects.create(
                            user=request.user,
                            shipping_address=form.cleaned_data['shipping_address'],
                            phone=form.cleaned_data['phone'],
                            notes=form.cleaned_data.get('notes', '')
                        )
                        
                        # Create order items and update stock
                        for item in cart.items.all():
                            OrderItem.objects.create(
                                order=order,
                                product=item.product,
                                quantity=item.quantity,
                                unit_price=item.price_at_time,
                                total_price=item.total_price,
                                farmer=item.product.farmer
                            )
                            
                            # Update stock quantity
                            product = item.product
                            product.stock_quantity -= item.quantity
                            product.save()
                            
                            # Check if product should be marked as unavailable
                            if product.stock_quantity <= 0:
                                product.is_available = False
                                product.save()
                        
                        # Clear cart after successful order
                        cart.items.all().delete()
                    
                    messages.success(
                        request,
                        f"Order placed successfully! Order ID: {order.id}"
                    )
                    return redirect('order-detail', order_id=order.id)
                
                except ValidationError as e:
                    messages.error(request, '; '.join(e.messages))
                except Exception as e:
                    messages.error(request, f"Error processing order: {str(e)}")
        else:
            form = ShippingAddressForm(user=request.user)
        
        context = {
            'form': form,
            'cart': cart,
            'cart_items': cart.items.select_related('product', 'product__farmer').all()
        }
        return render(request, 'shop/checkout.html', context)
    
    except Cart.DoesNotExist:
        messages.error(request, "Cart not found")
        return redirect('product-list')

class OrderListView(LoginRequiredMixin, ListView):
    """List all orders for the current user"""
    model = Order
    template_name = 'shop/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'shop/order_detail.html'
    context_object_name = 'order'
    pk_url_kwarg = 'order_id'

    def get_queryset(self):
        """Filter orders based on user type"""
        if self.request.user.is_farmer:
            # Farmers can only see orders containing their products
            return Order.objects.filter(items__farmer=self.request.user).distinct()
        else:
            # Customers can only see their own orders
            return Order.objects.filter(user=self.request.user)

class FarmerOrderDetailView(LoginRequiredMixin, FarmerRequiredMixin, DetailView):
    model = Order
    template_name = 'shop/farmer_order_detail.html'
    context_object_name = 'order'
    pk_url_kwarg = 'order_id'

    def get_queryset(self):
        """Filter orders to only show those containing products from this farmer"""
        return Order.objects.filter(items__farmer=self.request.user).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get only items belonging to this farmer
        context['farmer_items'] = self.object.items.filter(farmer=self.request.user)
        context['total_price'] = context['farmer_items'].aggregate(total=Sum('total_price'))['total'] or 0
        return context

@login_required
def update_order_status(request, order_id):
    """Update order status"""
    if not request.user.is_farmer:
        messages.error(request, "Only farmers can update order status")
        return redirect('farmer-orders')
    
    order = get_object_or_404(Order.objects.filter(items__farmer=request.user).distinct(), id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        reason = request.POST.get('reason', '')
        
        if order.update_status(new_status, reason):
            messages.success(request, f"Order status updated to {order.get_status_display()}")
            
            # Send notification to customer (implement your notification system)
            # notify_customer(order, new_status)
        else:
            messages.error(request, "Invalid status transition")
    
    return redirect('farmer-order-detail', order_id=order.id)

class FarmerOrderListView(LoginRequiredMixin, FarmerRequiredMixin, ListView):
    """List all orders containing products from the current farmer"""
    template_name = 'shop/farmer_orders.html'
    context_object_name = 'orders'
    paginate_by = 10
    
    def get_queryset(self):
        # Get orders that contain products from this farmer
        return Order.objects.filter(
            items__farmer=self.request.user
        ).distinct().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate total sales for this farmer
        total_sales = OrderItem.objects.filter(
            order__status__in=['delivered', 'out_for_delivery', 'packaging', 'accepted'],
            farmer=self.request.user
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')
        context['total_sales'] = total_sales
        return context

@login_required
def cancel_order(request, order_id):
    """Cancel an order"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify user has permission to cancel
    if not (request.user == order.user or 
            (request.user.is_farmer and order.items.filter(farmer=request.user).exists())):
        messages.error(request, "You don't have permission to cancel this order")
        return redirect('order-list')
    
    if not order.can_cancel():
        messages.error(request, "This order cannot be cancelled")
        return redirect('order-detail', order_id=order.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        status = 'customer_cancelled' if request.user == order.user else 'cancelled'
        
        if order.update_status(status, reason):
            # Restore stock quantities
            for item in order.items.all():
                item.product.stock_quantity = item.product.stock_quantity + item.quantity
                item.product.save()
            
            messages.success(request, "Order cancelled successfully")
            
            # Send notification to relevant parties (implement your notification system)
            # if request.user == order.user:
            #     notify_farmers(order, 'customer_cancelled')
            # else:
            #     notify_customer(order, 'cancelled')
        else:
            messages.error(request, "Failed to cancel order")
    
    return redirect('order-detail', order_id=order.id)

@login_required
def dashboard(request):
    # Common initialization
    cart = Cart.objects.filter(user=request.user).first()
    
    if request.user.is_farmer:
        products = Product.objects.filter(farmer=request.user)
        total_products = products.count()
        available_products = products.filter(
            is_available=True,
            stock_quantity__gt=0
        ).count()
        out_of_stock = products.filter(
            stock_quantity=0
        ).count()
        low_stock = products.filter(
            stock_quantity__gt=0,
            stock_quantity__lt=F('min_quantity')
        ).count()
        
        # Get recent orders for farmer's products
        recent_orders = Order.objects.filter(
            items__farmer=request.user
        ).distinct().order_by('-created_at')[:5]
        
        recent_products = products.select_related('category').order_by('-updated_at')[:5]
    else:
        # Customer dashboard
        recent_orders = Order.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        products = None
        total_products = available_products = out_of_stock = low_stock = 0
        recent_products = None

    context = {
        'total_products': total_products,
        'available_products': available_products,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'recent_products': recent_products,
        'recent_orders': recent_orders,
        'cart': cart
    }
    return render(request, 'shop/dashboard.html', context)
