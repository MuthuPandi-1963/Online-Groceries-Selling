# Generated by Django 5.1.7 on 2025-03-17 01:22

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0003_remove_order_cancelled_at_remove_order_delivered_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='price_at_time',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='cancellation_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='order',
            name='last_status_update',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'New Order'), ('accepted', 'Order Confirmed'), ('packaging', 'Packaging'), ('out_for_delivery', 'Out for Delivery'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled by Farmer'), ('customer_cancelled', 'Cancelled by Customer'), ('partially_delivered', 'Partially Delivered')], default='pending', max_length=20),
        ),
        migrations.AlterModelTable(
            name='order',
            table='orders',
        ),
    ]
