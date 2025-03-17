from django import forms
from django.core.exceptions import ValidationError
from .models import User, Product, Category, Cart, CartItem, Order

class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'is_farmer', 'phone', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Passwords do not match')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image', 'slug']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'base_price', 'unit', 
                 'min_quantity', 'stock_quantity', 'image', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'base_price': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'min_quantity': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }

class CartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'min': '0.01',
                'step': '0.01',
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if self.product:
            self.fields['quantity'].widget.attrs.update({
                'min': str(self.product.min_quantity),
                'max': str(self.product.stock_quantity),
                'step': '0.01' if self.product.unit in ['kg', 'l'] else '1',
            })
            # Set initial value to min_quantity
            self.fields['quantity'].initial = self.product.min_quantity

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.product:
            if quantity < self.product.min_quantity:
                raise ValidationError(
                    f'Minimum order quantity is {self.product.min_order_display}'
                )
            if quantity > self.product.stock_quantity:
                raise ValidationError(
                    f'Only {self.product.stock_display} available'
                )
        return quantity

class ShippingAddressForm(forms.Form):
    shipping_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Enter your complete shipping address'
        }),
        help_text='Please provide your complete delivery address including street, city, state, and PIN code.'
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your contact number'
        }),
        help_text='Phone number for delivery updates'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'Any special instructions for delivery'
        }),
        required=False,
        help_text='Optional: Add any special delivery instructions'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['shipping_address'].initial = user.address
            self.fields['phone'].initial = user.phone

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['shipping_address']
        widgets = {
            'shipping_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your shipping address'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['shipping_address'].initial = user.address
