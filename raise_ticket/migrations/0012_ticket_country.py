# Generated by Django 5.2.1 on 2025-05-28 10:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raise_ticket', '0011_alter_ticket_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='country',
            field=models.CharField(blank=True),
        ),
    ]
