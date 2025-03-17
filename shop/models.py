from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Sum, F, Q

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_farmer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.get_full_name() or self.username

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)

class Product(models.Model):
    UNIT_CHOICES = [
        ('g', 'Grams'),
        ('kg', 'Kilograms'),
        ('l', 'Liters'),
        ('ml', 'Milliliters'),
        ('pc', 'Pieces'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit = models.CharField(max_length=2, choices=UNIT_CHOICES, default='kg')
    min_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Minimum quantity that can be ordered'
    )
    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"

    def clean(self):
        super().clean()
        if not self.is_available and self.stock_quantity > 0:
            raise ValidationError("Product cannot be unavailable with stock > 0")
        if self.is_available and self.stock_quantity <= 0:
            raise ValidationError("Product cannot be available with no stock")
        if self.min_quantity > self.stock_quantity:
            raise ValidationError("Minimum order quantity cannot exceed stock quantity")

    def get_normalized_quantity(self, quantity):
        """Convert quantity to a normalized unit (kg/L) if using g/ml"""
        if self.unit in ['g', 'ml']:
            return quantity / 1000
        return quantity

    def get_display_unit(self):
        """Get the display unit, converting g to kg and ml to L for better readability"""
        if self.unit == 'g':
            return 'kg'
        elif self.unit == 'ml':
            return 'L'
        return self.get_unit_display()

    @property
    def formatted_price(self):
        """Format the price with the appropriate unit"""
        if self.unit in ['g', 'ml']:
            price_per_unit = (self.base_price * 1000) / self.min_quantity
            unit_display = 'kg' if self.unit == 'g' else 'L'
        else:
            price_per_unit = self.base_price
            unit_display = self.get_unit_display()
        
        return f"₹{price_per_unit:.2f}/{unit_display}"

    @property
    def stock_display(self):
        """Format the stock quantity with appropriate units"""
        quantity = self.stock_quantity
        
        if self.unit in ['g', 'ml']:
            if quantity >= 1000:
                return f"{quantity/1000:.1f} {'kg' if self.unit == 'g' else 'L'}"
            return f"{quantity:.0f} {self.get_unit_display()}"
        
        if self.unit == 'pc':
            return f"{int(quantity)} {self.get_unit_display()}"
        
        return f"{quantity:.2f} {self.get_unit_display()}"

    @property
    def min_order_display(self):
        """Format the minimum order quantity with appropriate units"""
        quantity = self.min_quantity
        
        if self.unit in ['g', 'ml']:
            if quantity >= 1000:
                return f"{quantity/1000:.1f} {'kg' if self.unit == 'g' else 'L'}"
            return f"{quantity:.0f} {self.get_unit_display()}"
        
        if self.unit == 'pc':
            return f"{int(quantity)} {self.get_unit_display()}"
        
        return f"{quantity:.2f} {self.get_unit_display()}"

    @property
    def stock_status(self):
        """Get the stock status for display"""
        if not self.is_available:
            return 'unavailable'
        if self.stock_quantity == 0:
            return 'out_of_stock'
        if self.stock_quantity < self.min_quantity:
            return 'low_stock'
        return 'in_stock'

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_price(self):
        """Calculate total price of all items"""
        total = Decimal('0.00')
        for item in self.items.all():
            if item.price_at_time and item.quantity:
                total += item.price_at_time * item.quantity
        return total

    @property
    def total_with_delivery(self):
        """Calculate total including delivery fee"""
        delivery_fee = Decimal('50.00')  # Move to settings later
        return self.total_price + delivery_fee

    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()
        self.save()

    def get_farmer_items(self, farmer):
        """Get all items from a specific farmer"""
        return self.items.filter(product__farmer=farmer)

    def get_farmer_total(self, farmer):
        """Calculate total for a specific farmer's items"""
        total = Decimal('0.00')
        for item in self.get_farmer_items(farmer):
            if item.price_at_time and item.quantity:
                total += item.price_at_time * item.quantity
        return total

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    price_at_time = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,  # Allow null temporarily for migration
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def save(self, *args, **kwargs):
        # Always ensure price_at_time is set to current product price
        if not self.price_at_time:
            self.price_at_time = self.product.base_price
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.price_at_time if self.price_at_time else Decimal('0.00')

    def clean(self):
        """Validate cart item"""
        super().clean()
        if not self.product.is_available:
            raise ValidationError("This product is not available")
        if self.quantity > self.product.stock_quantity:
            raise ValidationError(f"Only {self.product.stock_display} available")
        if self.quantity < self.product.min_quantity:
            raise ValidationError(f"Minimum order quantity is {self.product.min_order_display}")

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'New Order'),
        ('accepted', 'Order Confirmed'),
        ('packaging', 'Packaging'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled by Farmer'),
        ('customer_cancelled', 'Cancelled by Customer'),
        ('partially_delivered', 'Partially Delivered'),
    ]

    VALID_STATUS_TRANSITIONS = {
        'pending': ['accepted', 'cancelled', 'customer_cancelled'],
        'accepted': ['packaging', 'cancelled', 'customer_cancelled'],
        'packaging': ['out_for_delivery', 'cancelled', 'customer_cancelled'],
        'out_for_delivery': ['delivered', 'partially_delivered', 'cancelled'],
        'partially_delivered': ['delivered', 'cancelled'],
        'delivered': [],
        'cancelled': [],
        'customer_cancelled': [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField()
    phone = models.CharField(max_length=15, default='')  
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_status_update = models.DateTimeField(auto_now_add=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} ({self.get_status_display()})"

    @property
    def total(self):
        """Calculate total order amount"""
        return self.items.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0.00')

    def can_transition_to(self, new_status):
        """Check if the order can transition to the new status"""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])

    def update_status(self, new_status, reason=''):
        """Update order status with validation"""
        if not self.can_transition_to(new_status):
            raise ValidationError(
                f"Invalid status transition from {self.get_status_display()} to {new_status}"
            )
        
        self.status = new_status
        self.last_status_update = timezone.now()
        
        if new_status in ['cancelled', 'customer_cancelled']:
            self.cancellation_reason = reason
        
        self.save()

    def can_cancel(self):
        """Check if the order can be cancelled"""
        return self.status in ['pending', 'accepted', 'packaging']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    farmer = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity} {self.product.get_unit_display()} of {self.product.name}"

    def save(self, *args, **kwargs):
        # Calculate total price before saving
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        
        # Set farmer if not set
        if not self.farmer_id:
            self.farmer = self.product.farmer
            
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.quantity > self.product.stock_quantity:
            raise ValidationError(f"Insufficient stock. Only {self.product.stock_display} available")
